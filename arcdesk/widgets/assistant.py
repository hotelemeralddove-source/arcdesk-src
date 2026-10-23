"""The ARC console — where you actually talk to the assistant.

A QTextBrowser transcript (one widget, not N message widgets: cheap and scrolls
well), a single-line input, a mic button and suggestion chips.
"""
from __future__ import annotations

import html
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget,
)

SUGGESTIONS = [
    ("SYSTEM REPORT", "system report"),
    ("OPEN NOTEPAD", "open notepad"),
    ("FOCUS MODE", "switch to focus mode"),
    ("TIMER 10 MIN", "timer 10 minutes"),
    ("SCREENSHOT", "take a screenshot"),
]


class AssistantConsole(QWidget):
    submitted = Signal(str)
    mic_requested = Signal()
    settings_requested = Signal()
    reset_requested = Signal()
    replay_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("console")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # ---- header ----------------------------------------------------
        head = QHBoxLayout()
        head.setSpacing(10)
        title = QLabel("ARC CONSOLE")
        title.setObjectName("consoleTitle")
        f = title.font()
        f.setPixelSize(10)
        f.setWeight(f.Weight.Bold)
        f.setLetterSpacing(f.SpacingType.AbsoluteSpacing, 2.6)
        title.setFont(f)
        head.addWidget(title)

        self.status = QLabel("booting…")
        self.status.setObjectName("consoleStatus")
        fs = self.status.font()
        fs.setPixelSize(9)
        fs.setLetterSpacing(fs.SpacingType.AbsoluteSpacing, 1.4)
        self.status.setFont(fs)
        head.addWidget(self.status)
        head.addStretch(1)

        for text, tip, slot in (
            ("C", "Clear conversation", self.reset_requested.emit),
            ("▶", "Replay last answer aloud", self.replay_requested.emit),
            ("*", "Assistant settings", self.settings_requested.emit),
        ):
            b = QPushButton(text)
            b.setObjectName("iconBtn")
            b.setFixedSize(26, 24)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            head.addWidget(b)
        lay.addLayout(head)

        # ---- transcript -------------------------------------------------
        self.view = QTextBrowser()
        self.view.setObjectName("transcript")
        self.view.setOpenExternalLinks(True)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setMinimumHeight(190)
        lay.addWidget(self.view, 1)
        self._last_arc = ""

        # ---- suggestion chips -------------------------------------------
        chips = QHBoxLayout()
        chips.setSpacing(6)
        for label, command in SUGGESTIONS:
            c = QPushButton(label)
            c.setObjectName("chip2")
            c.setCursor(Qt.CursorShape.PointingHandCursor)
            c.clicked.connect(lambda _=False, cmd=command: self._submit(cmd))
            chips.addWidget(c)
        chips.addStretch(1)
        lay.addLayout(chips)

        # ---- input ------------------------------------------------------
        row = QHBoxLayout()
        row.setSpacing(8)
        self.input = QLineEdit()
        self.input.setObjectName("chatInput")
        self.input.setPlaceholderText("Talk to ARC…  (e.g. open notepad, what's my cpu usage)")
        self.input.returnPressed.connect(lambda: self._submit(self.input.text()))
        row.addWidget(self.input, 1)

        self.mic = QPushButton("MIC")
        self.mic.setObjectName("micBtn")
        self.mic.setFixedSize(42, 34)
        self.mic.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic.setToolTip("Hold a conversation (Windows dictation)")
        self.mic.clicked.connect(self.mic_requested.emit)
        row.addWidget(self.mic)

        self.send = QPushButton("SEND")
        self.send.setObjectName("sendBtn")
        self.send.setFixedSize(64, 34)
        self.send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send.clicked.connect(lambda: self._submit(self.input.text()))
        row.addWidget(self.send)
        lay.addLayout(row)

    # -- api -------------------------------------------------------------
    def _submit(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self.input.clear()
        self.submitted.emit(text)

    def focus_input(self) -> None:
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    @property
    def last_answer(self) -> str:
        return self._last_arc

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_busy(self, busy: bool) -> None:
        self.send.setEnabled(not busy)
        self.send.setText("…" if busy else "SEND")
        if busy:
            self.status.setText("THINKING…")

    # -- transcript ------------------------------------------------------
    def _bubble(self, who: str, text: str, cls: str) -> None:
        stamp = time.strftime("%H:%M")
        self.view.append(
            f'<div class="row {cls}"><div class="meta">{who} · {stamp}</div>'
            f'<div class="msg">{html.escape(text).replace(chr(10), "<br>")}</div></div>'
        )
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def add_user(self, text: str) -> None:
        self._bubble("YOU", text, "user")

    def add_arc(self, text: str) -> None:
        self._last_arc = text
        self._bubble("ARC", text, "arc")

    def add_tool(self, name: str, args: str, result: str) -> None:
        short = result if len(result) <= 150 else result[:150] + "…"
        self.view.append(
            f'<div class="row tool"><div class="meta">TOOL · {html.escape(name)} '
            f'{html.escape(args)[:80]}</div>'
            f'<div class="msg">{html.escape(short)}</div></div>'
        )
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def add_note(self, text: str) -> None:
        self.view.append(f'<div class="row note"><div class="msg">{html.escape(text)}</div></div>')
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def clear_view(self) -> None:
        self.view.clear()

    def apply_doc_style(self, th) -> None:
        """Transcript bubbles are HTML, so they get their own stylesheet."""
        from PySide6.QtGui import QColor
        dim = QColor(th.dim).lighter(155).name()
        self.view.document().setDefaultStyleSheet(f"""
            .row {{ margin: 0 0 8px 0; }}
            .meta {{ font-size: 8.5px; letter-spacing: 1.3px; color: {dim}; }}
            .msg {{ font-size: 12.5px; line-height: 145%; margin-top: 2px; }}
            .user .msg {{ color: {th.text}; }}
            .user .meta {{ color: {dim}; }}
            .arc .msg {{ color: {th.accent}; }}
            .tool .msg {{ color: {dim}; font-size: 10.5px; }}
            .note .msg {{ color: {dim}; font-style: italic; font-size: 10.5px; }}
        """)

    def styles(self, th) -> str:
        from PySide6.QtGui import QColor
        dim = QColor(th.dim).lighter(150).name()
        return f"""
            QWidget#console {{ background: transparent; }}
            QLabel#consoleTitle {{ color: {th.accent}; }}
            QLabel#consoleStatus {{ color: {dim}; }}
            QTextBrowser#transcript {{
                background: rgba(0,0,0,0.28);
                border: 1px solid rgba({QColor(th.accent).red()},{QColor(th.accent).green()},
                                        {QColor(th.accent).blue()},0.16);
                border-radius: 12px; padding: 8px; color: {th.text};
                font-size: 12px;
            }}
            QLineEdit#chatInput {{
                background: rgba({QColor(th.accent).red()},{QColor(th.accent).green()},
                                 {QColor(th.accent).blue()},0.08);
                border: 1px solid rgba({QColor(th.accent).red()},{QColor(th.accent).green()},
                                       {QColor(th.accent).blue()},0.30);
                border-radius: 10px; padding: 8px 12px; color: {th.text};
                selection-background-color: {th.accent};
            }}
            QLineEdit#chatInput:focus {{ border-color: {th.accent}; }}
            QPushButton#sendBtn {{ background: {th.accent}; color: #04090f;
                                   border: none; border-radius: 10px;
                                   font-size: 10px; font-weight: 700;
                                   letter-spacing: 1.4px; }}
            QPushButton#sendBtn:disabled {{ background: rgba({QColor(th.accent).red()},
                                            {QColor(th.accent).green()},
                                            {QColor(th.accent).blue()},0.30);
                                            color: {dim}; }}
            QPushButton#micBtn {{ background: transparent; color: {dim};
                                  border: 1px solid rgba({QColor(th.accent).red()},
                                  {QColor(th.accent).green()},{QColor(th.accent).blue()},0.30);
                                  border-radius: 10px; font-size: 9px; font-weight: 700; letter-spacing: 0.6px; }}
            QPushButton#micBtn:hover {{ color: {th.accent}; border-color: {th.accent}; }}
            QPushButton#chip2 {{ background: rgba({QColor(th.accent).red()},
                                 {QColor(th.accent).green()},{QColor(th.accent).blue()},0.07);
                                 color: {dim}; border: 1px solid rgba({QColor(th.accent).red()},
                                 {QColor(th.accent).green()},{QColor(th.accent).blue()},0.20);
                                 border-radius: 9px; padding: 4px 9px;
                                 font-size: 8.5px; font-weight: 600; letter-spacing: 1.1px; }}
            QPushButton#chip2:hover {{ color: {th.accent}; border-color: {th.accent}; }}
            QPushButton#iconBtn {{ background: transparent; color: {dim}; border: none;
                                   border-radius: 7px; font-size: 12px; }}
            QPushButton#iconBtn:hover {{ color: {th.accent}; background: rgba(
                                        {QColor(th.accent).red()},{QColor(th.accent).green()},
                                        {QColor(th.accent).blue()},0.14); }}
        """
