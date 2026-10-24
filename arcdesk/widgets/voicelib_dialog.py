"""Settings → Voice → "Voices…" — two lists, because there are two questions.

    COMMAND VOICES   who may say "hey jarvis" and be obeyed   (any number of people)
    REPLY VOICE      which voice ARC answers in              (any voice you have a clip of)

The user asked for exactly this: command in my voice, reply in the voice I choose — and no
robotic TTS. The honesty is on the screen: a reply voice needs a clone engine installed
(IndicF5 / XTTS), and until one is, ARC says "system voice" rather than pretending.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from .. import voicelib
from ..theme import Theme


def _heading(text: str) -> QLabel:
    lab = QLabel(text)
    f = lab.font()
    f.setPixelSize(10)
    f.setWeight(f.Weight.Bold)
    lab.setFont(f)
    return lab


class VoiceLibraryDialog(QDialog):
    def __init__(self, cfg: dict, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.theme = theme
        self.setWindowTitle("Arc Desk · voices")
        self.setMinimumSize(640, 660)
        from .style import dialog_style
        if theme:
            self.setStyleSheet(dialog_style(theme))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)

        title = QLabel("VOICES")
        f = title.font()
        f.setPixelSize(11)
        f.setWeight(f.Weight.Bold)
        title.setFont(f)
        lay.addWidget(title)
        lay.addWidget(QLabel(
            "Two different things. Who may COMMAND ARC, and which voice it ANSWERS in."))

        # ------------------------------------------------------------ command
        lay.addWidget(_heading("1 · WHO MAY COMMAND IT"))
        self.cmd_list = QListWidget()
        self.cmd_list.setMaximumHeight(90)
        lay.addWidget(self.cmd_list)
        row = QHBoxLayout()
        self.cmd_name = QLineEdit()
        self.cmd_name.setPlaceholderText("name (e.g. me, amma, ravi)")
        row.addWidget(self.cmd_name, 1)
        self.cmd_add = QPushButton("Add a voice…")
        self.cmd_add.clicked.connect(self._add_command)
        row.addWidget(self.cmd_add)
        self.cmd_del = QPushButton("Remove")
        self.cmd_del.clicked.connect(self._del_command)
        row.addWidget(self.cmd_del)
        lay.addLayout(row)
        self.cmd_note = QLabel("")
        self.cmd_note.setWordWrap(True)
        lay.addWidget(self.cmd_note)

        # -------------------------------------------------------------- reply
        lay.addWidget(_heading("2 · THE VOICE ARC ANSWERS IN"))
        self.reply_list = QListWidget()
        self.reply_list.setMaximumHeight(110)
        lay.addWidget(self.reply_list)
        row2 = QHBoxLayout()
        self.reply_name = QLineEdit()
        self.reply_name.setPlaceholderText("name for this voice (e.g. rajini, me)")
        row2.addWidget(self.reply_name, 1)
        self.reply_add = QPushButton("Add a voice…")
        self.reply_add.clicked.connect(self._add_reply)
        row2.addWidget(self.reply_add)
        row2.addStretch(1)
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        self.use = QPushButton("Answer in this voice")
        self.use.clicked.connect(self._use_reply)
        row3.addWidget(self.use)
        self.hear = QPushButton("Hear it")
        self.hear.clicked.connect(self._hear)
        row3.addWidget(self.hear)
        self.reply_del = QPushButton("Remove")
        self.reply_del.clicked.connect(self._del_reply)
        row3.addWidget(self.reply_del)
        row3.addStretch(1)
        lay.addLayout(row3)

        lay.addWidget(_heading("WHAT IT SAYS IN THAT CLIP"))
        self.transcript = QLineEdit()
        self.transcript.setPlaceholderText("type the words spoken in the clip (needed by IndicF5)")
        lay.addWidget(self.transcript)
        self.lang = QComboBox()
        for label, code in (("Auto (from the script)", "auto"), ("Tamil", "ta"),
                            ("Hindi", "hi"), ("English", "en")):
            self.lang.addItem(label, code)
        lay.addWidget(self.lang)

        from .style import read_only_log
        self.out = read_only_log(QPlainTextEdit())
        self.out.setFixedHeight(130)
        lay.addWidget(self.out)

        row4 = QHBoxLayout()
        self.engine_btn = QPushButton("The engine that makes it sound real…")
        self.engine_btn.setToolTip("IndicF5 for Tamil/Hindi, XTTS for English — downloaded "
                                  "once, from here, one click.")
        self.engine_btn.clicked.connect(self.open_engines)
        row4.addWidget(self.engine_btn)
        row4.addStretch(1)
        done = QPushButton("Done")
        done.clicked.connect(self.accept)
        row4.addWidget(done)
        lay.addLayout(row4)

        self._reload()

    # ------------------------------------------------------------------ lists
    def _reload(self) -> None:
        self.cmd_list.clear()
        for name in voicelib.command_voices():
            self.cmd_list.addItem(QListWidgetItem(name))
        self.reply_list.clear()
        active = voicelib.active_reply().get("id", "")
        for entry in voicelib.reply_voices():
            label = (f"{entry['name']}  ·  {entry.get('seconds', 0):g} s · "
                     f"{entry.get('grade', '')}"
                     + ("   ← in use" if entry.get("id") == active else ""))
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry.get("id", ""))
            self.reply_list.addItem(item)
        self.cmd_note.setText(
            ("Nobody is enrolled: any voice may command ARC." if not voicelib.command_voices()
             else "Enrolled: " + ", ".join(voicelib.command_voices())
                  + ". The lock must also be ON (the switch on the Voice tab)."))
        self.out.setPlainText(voicelib.describe() + "\n\n" + self._engine_line())

    def _engine_line(self) -> str:
        """One honest sentence about the engine, then the way to get it."""
        try:
            from .. import engines
            return engines.line_for_voice()
        except Exception:
            return "No clone engine is installed, so replies use the system voice."

    def open_engines(self) -> None:
        from .engine_dialog import EngineDialog
        EngineDialog(self.theme, parent=self).exec()
        self._reload()

    # -------------------------------------------------------------- commands
    def _add_command(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "A recording of the voice allowed to command ARC", "",
            "Audio or video (*.wav *.mp3 *.m4a *.mp4 *.mkv *.webm *.ogg *.flac);;All files (*)")
        if not path:
            return
        got = voicelib.add_command(self.cmd_name.text(), path)
        self.out.setPlainText(got.get("message", ""))
        self._reload()

    def _del_command(self) -> None:
        item = self.cmd_list.currentItem()
        if item is None:
            return
        voicelib.remove_command(item.text())
        self._reload()

    # ------------------------------------------------------------------ reply
    def _add_reply(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "A recording of the voice ARC should answer in", "",
            "Audio or video (*.wav *.mp3 *.m4a *.mp4 *.mkv *.webm *.ogg *.flac);;All files (*)")
        if not path:
            return
        got = voicelib.add_reply(self.reply_name.text(), path, self.transcript.text(),
                                 self.lang.currentData() or "auto")
        if not got.get("ok"):
            self.out.setPlainText("could not add that voice:\n" + str(got.get("message")))
            return
        voicelib.set_reply(got["voice"]["id"])
        self.out.setPlainText(got["message"] + "\n\n" + voicelib.describe())
        self._reload()

    def _use_reply(self) -> None:
        item = self.reply_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Pick one", "Choose a voice in the list first.")
            return
        if voicelib.set_reply(item.data(Qt.ItemDataRole.UserRole)):
            self.out.setPlainText("now answering in that voice.\n\n" + voicelib.describe())
        self._reload()

    def _del_reply(self) -> None:
        item = self.reply_list.currentItem()
        if item is None:
            return
        voicelib.remove_reply(item.data(Qt.ItemDataRole.UserRole))
        self._reload()

    def _hear(self) -> None:
        from .. import clone
        entry = voicelib.active_reply()
        if not entry:
            self.out.setPlainText("add a reply voice first")
            return
        lang = entry.get("lang") or "auto"
        if lang == "auto":
            lang = "ta" if any("\u0b80" <= ch <= "\u0bff" for ch in entry.get("transcript", "")) \
                else ("hi" if any("\u0900" <= ch <= "\u097f" for ch in entry.get("transcript", ""))
                      else "en")
        line = {"ta": "vanakkam, ithu nee kodutha kural.",
                "hi": "namaste, yah wahi aawaz hai.",
                "en": "hello, this is the voice you gave me."}.get(lang, "hello")
        ok = clone.speak(line, lang)
        self.out.setPlainText(("heard: " + line) if ok else
                             "nothing spoke — install_clone.bat (IndicF5 / XTTS) first.")
