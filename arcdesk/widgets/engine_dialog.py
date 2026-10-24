"""Get the reply-voice engine — in the app, one click, no command prompt.

The point of this screen: a cloned voice is not a preference, it is a 1.5 GB model. So the
person gets one button per engine, the size written on the button, live output while it
downloads, a Stop button that actually stops, and a result line that is either "ready" or
the real reason it is not. No "installing…" that never ends, and no success message that
the app cannot back up.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QPlainTextEdit,
                               QProgressBar, QPushButton, QVBoxLayout, QWidget)

from .. import engines


class _Worker(QThread):
    line = Signal(str)
    done = Signal(dict)

    def __init__(self, engine: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.cancel = threading.Event()

    def run(self) -> None:  # pragma: no cover - real process, exercised by the app
        result = engines.install(self.engine, on_line=self.line.emit, cancel=self.cancel)
        self.done.emit(result)

    def stop(self) -> None:
        self.cancel.set()


class EngineDialog(QDialog):
    """Two engines, their real sizes, their real state, and one button each."""

    def __init__(self, theme: dict | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme or {}
        self.setWindowTitle("Voice engines — what makes a clone sound real")
        self.setMinimumSize(720, 560)
        self._worker: _Worker | None = None
        from .style import dialog_style
        if self.theme:
            self.setStyleSheet(dialog_style(self.theme))

        root = QVBoxLayout(self)
        title = QLabel("A cloned voice needs a neural engine")
        title.setObjectName("h1")
        root.addWidget(title)
        intro = QLabel(
            "Without one, ARC answers in the system voice — and says so. With one, it "
            "speaks in the voice you picked, in that person's own sound.\n"
            "Downloaded once, kept on this computer. Nothing is installed behind your back.")
        intro.setObjectName("dim")
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.picker = QComboBox()
        self.picker.currentIndexChanged.connect(lambda _i: self._show())
        root.addWidget(self.picker)

        self.state = QLabel("")
        self.state.setObjectName("dim")
        self.state.setWordWrap(True)
        root.addWidget(self.state)

        row = QHBoxLayout()
        self.go = QPushButton("Install now")
        self.go.clicked.connect(self._start)
        row.addWidget(self.go)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        row.addWidget(self.stop_btn)
        self.check = QPushButton("Check again")
        self.check.clicked.connect(self.reload)
        row.addWidget(self.check)
        row.addStretch(1)
        root.addLayout(row)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)          # indeterminate: pip does not report percentages
        self.bar.setVisible(False)
        root.addWidget(self.bar)

        from .style import read_only_log
        self.log = read_only_log(QPlainTextEdit())
        root.addWidget(self.log, 1)

        self.verdict = QLabel("")
        self.verdict.setObjectName("verdict")
        self.verdict.setWordWrap(True)
        root.addWidget(self.verdict)

        self._items: dict[str, dict] = {}
        self._verdict_for = ""          # which engine the verdict below is about
        self.reload()

    # ------------------------------------------------------------------ state
    def reload(self) -> None:
        from .. import clone
        clone.refresh()
        self._items = engines.status()
        keep = self.picker.currentData()
        self.picker.blockSignals(True)
        self.picker.clear()
        for key, v in self._items.items():
            mark = "✔ ready" if v["ready"] else f"missing · {v['size_mb']} MB"
            self.picker.addItem(f"{v['label']} — {v['langs']} — {mark}", key)
        self.picker.blockSignals(False)
        if keep:
            i = self.picker.findData(keep)
            if i >= 0:
                self.picker.setCurrentIndex(i)
        self._show()

    def _current(self) -> dict:
        return self._items.get(self.picker.currentData() or "", {})

    def _show(self) -> None:
        v = self._current()
        if not v:
            return
        m = engines.method()
        if v["ready"]:
            self.state.setText(f"<b>{v['label']} is ready.</b> {v['why'].rstrip('.')} — "
                               f"replies in {v['langs']} use the voice you picked.")
            self.go.setText("Reinstall / repair")
        else:
            self.state.setText(
                f"<b>{v['label']} is not installed.</b> It is the engine for "
                f"{v['langs']} — {v['why'].rstrip('.')}. About "
                f"{v['size_mb'] / 1000:.1f} GB, once. {v['needs'].rstrip('.')}.")
            self.go.setText(f"Install {v['label']} ({v['size_mb'] / 1000:.1f} GB)")
        self.go.setEnabled(m["can_install"] and self._worker is None)
        if not m["can_install"]:
            self.verdict.setText(
                "This build cannot add packages by itself: " + m["why"] +
                ". Double-click install_clone.bat in the app folder — it prints its own "
                "progress and takes one word from you (y / n).")
        elif self._verdict_for != v["id"]:
            self.verdict.setText("")   # a verdict about XTTS must not sit under IndicF5

    # ------------------------------------------------------------------ actions
    def _start(self) -> None:
        v = self._current()
        if not v or self._worker is not None:
            return
        self.log.clear()
        self.log.appendPlainText(f"installing {v['label']} · about {v['size_mb']} MB…")
        self.bar.setVisible(True)
        self.go.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.verdict.setText("")
        self._verdict_for = v["id"]
        w = _Worker(v["id"], self)
        w.line.connect(self.log.appendPlainText)
        w.done.connect(self._finished)
        self._worker = w
        w.start()

    def _stop(self) -> None:
        if self._worker is not None:
            self.log.appendPlainText("— stopping, as asked —")
            self._worker.stop()
            self.stop_btn.setEnabled(False)

    def _finished(self, result: dict) -> None:
        self._worker = None
        self._verdict_for = result.get("engine", "")
        self.bar.setVisible(False)
        self.stop_btn.setEnabled(False)
        self.go.setEnabled(True)
        if result.get("ok"):
            self.verdict.setText(
                f"Done — {engines.SPECS[result['engine']]['label']} is installed. "
                "Replies in that language now use the voice you chose.")
        elif result.get("why") == "cancelled":
            self.verdict.setText("Stopped. Nothing was half-installed that matters — "
                                 "you can start again whenever you like.")
        else:
            self.verdict.setText(
                f"Not installed ({result.get('why') or 'failed'}). The last line above says "
                "why. ARC keeps saying “system voice” until this works — it will not fake it.")
        self.reload()
