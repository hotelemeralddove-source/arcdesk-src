"""The Magic screen — the "whole system changed" view.

A frameless fullscreen window that covers everything, including the taskbar, and
paints our own ARC workspace: reactor, clock, app grid, and a command line.

It is still *just a window*, which is exactly why it is safe: your Windows session
underneath is untouched, and the moment this hides, you are back — no shell
restart, no reboot, no lost Start menu.
"""
from __future__ import annotations

import math
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QLinearGradient, QPainter,
                           QPen, QRadialGradient)
from PySide6.QtWidgets import QGridLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ..theme import Theme
from .holo import HoloDeck
from ..ticker import ticker

APPS = [
    ("FILES", "explorer"), ("NOTEPAD", "notepad"), ("CALC", "calc"),
    ("TASK MGR", "taskmgr"), ("SETTINGS", "settings"), ("BROWSER", "https://www.google.com"),
]


class MagicScreen(QWidget):
    exit_requested = Signal()
    command = Signal(str)
    app_requested = Signal(str)

    def __init__(self, theme: Theme, exit_phrase: str = "bye jarvis") -> None:
        super().__init__()
        self._theme = theme
        self._exit_phrase = exit_phrase
        self._t = 0.0
        self._status = "MAGIC MODE ACTIVE"

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(5)

        # app grid: fixed width block, centred, so it never drifts over the reactor
        self._apps = QWidget()
        grid = QGridLayout(self._apps)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)
        self._buttons: list[QPushButton] = []
        for i, (label, target) in enumerate(APPS):
            b = QPushButton(label)
            b.setObjectName("magicApp")
            b.setFixedSize(136, 56)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, t=target: self.app_requested.emit(t))
            grid.addWidget(b, i // 3, i % 3)
            self._buttons.append(b)
        self._apps.setFixedWidth(3 * 136 + 2 * 12)
        lay.addWidget(self._apps, 0, Qt.AlignmentFlag.AlignHCenter)

        lay.addSpacing(26)
        self.input = QLineEdit()
        self.input.setObjectName("magicInput")
        self.input.setPlaceholderText('Speak, or type — "open google"  ·  "system report"')
        self.input.setMinimumHeight(38)
        self.input.setMinimumWidth(540)
        self.input.setMaximumWidth(560)
        self.input.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.input.returnPressed.connect(self._submit)
        lay.addWidget(self.input, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(3)

        # one renderer, painted into this widget's painter (no child widget, so
        # the buttons and the input stay above it without z-order tricks)
        self._holo = HoloDeck(theme)
        self._holo.autonomous = False

        self.setStyleSheet(self._qss(theme))
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self.update)
        self._clock.start()
        ticker().tick.connect(self._on_tick)

    # -- geometry --------------------------------------------------------
    def show_fullscreen(self) -> None:
        screens = QGuiApplication.screens()
        if screens:
            # cover the whole virtual desktop so every monitor is ARC
            geo = screens[0].geometry()
            for s in screens[1:]:
                geo = geo.united(s.geometry())
            self.setGeometry(geo)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(80, self.input.setFocus)

    def set_exit_phrase(self, phrase: str) -> None:
        self._exit_phrase = phrase
        self.update()

    def set_status(self, text: str) -> None:
        self._status = text
        self.update()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        if self._holo is not None:
            self._holo.set_theme(theme)
        self.setStyleSheet(self._qss(theme))
        self.update()

    # -- behaviour -------------------------------------------------------
    def _submit(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        low = text.lower()
        if self._exit_phrase and self._exit_phrase in low:
            self.exit_requested.emit()
            return
        self.command.emit(text)

    def _on_tick(self, dt: float) -> None:
        if not self.isVisible():
            return
        self._t += dt
        if self._holo is not None:
            self._holo.step(dt)
        self.update()

    def advance(self, seconds: float) -> None:
        self._t += seconds
        if self._holo is not None:
            self._holo.step(seconds)
        self.update()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.exit_requested.emit()
        else:
            super().keyPressEvent(event)

    # -- painting --------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        th = self._theme
        q = QPainter(self)
        q.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w * 0.5, h * 0.28

        # The hologram deck is the surface. Below 0.2 effect scale (Gaming mode)
        # it is skipped entirely, because a laptop playing a game should not be
        # rasterising a starfield for its desktop overlay.
        deck_on = self._holo is not None and th.effects >= 0.2
        if deck_on:
            self._holo.paint_onto(q, w, h, compact=True, ticker_bar=False)
        else:
            grad = QLinearGradient(0, 0, w * 0.35, h)
            grad.setColorAt(0.0, QColor(th.panel))
            grad.setColorAt(0.6, QColor(th.bg))
            grad.setColorAt(1.0, QColor(th.bg).darker(115))
            q.fillRect(0, 0, w, h, grad)

        accent = th.q("accent")
        accent2 = th.q("accent2")

        if deck_on:
            # The deck is the surface; all this screen adds is a soft plate so the
            # app buttons keep their contrast where the globe is brightest.
            plate = QRectF(cx - 260, h * 0.575, 520, h * 0.33)
            pg = QRadialGradient(plate.center(), max(plate.width(), plate.height()) * 0.62)
            pg.setColorAt(0.0, QColor(2, 12, 18, 165))
            pg.setColorAt(1.0, QColor(2, 12, 18, 0))
            q.setPen(Qt.PenStyle.NoPen)
            q.setBrush(pg)
            q.drawRect(plate)
        else:
            # ---- big ambient reactor -----------------------------------
            radius = min(w, h) * 0.18
            halo = QRadialGradient(QPointF(cx, cy), radius)
            halo.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 44))
            halo.setColorAt(1.0, QColor(accent.red(), accent.green(), accent.blue(), 0))
            q.setPen(Qt.PenStyle.NoPen)
            q.setBrush(halo)
            q.drawEllipse(QPointF(cx, cy), radius, radius)

            q.setBrush(Qt.BrushStyle.NoBrush)
            for i, f in enumerate((1.0, 0.72, 0.46)):
                col = accent if i % 2 == 0 else accent2
                q.setPen(QPen(QColor(col.red(), col.green(), col.blue(), 55 - i * 12), 1.6))
                q.drawEllipse(QPointF(cx, cy), radius * f, radius * f)

            # rotating arcs
            for i, (span, dirn, col) in enumerate(((78, 1.0, accent), (52, -1.4, accent2))):
                q.setPen(QPen(QColor(col.red(), col.green(), col.blue(), 200),
                              max(2.0, radius * 0.012),
                              Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
                rect = QRectF(cx - radius * 0.86, cy - radius * 0.86,
                              radius * 1.72, radius * 1.72)
                q.drawArc(rect, int((self._t * 26 * dirn + i * 130) * 16), int(span * 16))

            # centre glow
            core = QRadialGradient(QPointF(cx, cy), radius * 0.30)
            core.setColorAt(0.0, QColor(255, 255, 255, 235))
            core.setColorAt(0.35, QColor(accent.red(), accent.green(), accent.blue(), 180))
            core.setColorAt(1.0, QColor(accent.red(), accent.green(), accent.blue(), 0))
            q.setBrush(core)
            q.setPen(Qt.PenStyle.NoPen)
            pulse = 1.0 + 0.03 * math.sin(self._t * 2.0)
            q.drawEllipse(QPointF(cx, cy), radius * 0.30 * pulse, radius * 0.30 * pulse)

            # ---- clock --------------------------------------------------
            now = datetime.now()
            f = QFont("Segoe UI", 1)
            f.setPixelSize(int(min(w, h) * 0.058))
            f.setWeight(QFont.Weight.Light)
            q.setFont(f)
            q.setPen(QColor(th.text))
            time_text = now.strftime("%H:%M")
            fm = q.fontMetrics()
            q.drawText(QPointF(cx - fm.horizontalAdvance(time_text) / 2,
                               cy + f.pixelSize() * 0.28), time_text)

            f2 = QFont("Segoe UI", 1)
            f2.setPixelSize(max(11, int(min(w, h) * 0.016)))
            f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3.4)
            q.setFont(f2)
            q.setPen(QColor(th.dim).lighter(160))
            date_text = now.strftime("%A · %d %B %Y").upper()
            fm2 = q.fontMetrics()
            q.drawText(QPointF(cx - fm2.horizontalAdvance(date_text) / 2,
                               cy + f.pixelSize() * 0.28 + f2.pixelSize() * 2.1), date_text)

        # ---- status + exit hint -----------------------------------------
        f3 = QFont("Segoe UI", 1)
        f3.setPixelSize(max(9, int(min(w, h) * 0.012)))
        f3.setWeight(QFont.Weight.Bold)
        f3.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4.0)
        q.setFont(f3)
        q.setPen(accent)
        fm3 = q.fontMetrics()
        q.drawText(QPointF(cx - fm3.horizontalAdvance(self._status) / 2, h * 0.055),
                   self._status)

        hint = f'SAY "{self._exit_phrase.upper()}"  ·  ESC  ·  BACK TO NORMAL WINDOWS'
        q.setPen(QColor(th.dim).lighter(140))
        fm4 = q.fontMetrics()
        q.drawText(QPointF(cx - fm4.horizontalAdvance(hint) / 2, h * 0.955), hint)

        # ---- corner brackets --------------------------------------------
        q.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 120), 2.0))
        pad, arm = 26, 52
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = pad if sx > 0 else w - pad
            y = pad if sy > 0 else h - pad
            q.drawLine(QPointF(x, y), QPointF(x + sx * arm, y))
            q.drawLine(QPointF(x, y), QPointF(x, y + sy * arm))
        q.end()

    # -- style -----------------------------------------------------------
    def _qss(self, th: Theme) -> str:
        return f"""
            QPushButton#magicApp {{
                color: {th.accent}; background: rgba(0,0,0,0.30);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 14px; font-size: 11px; font-weight: 700;
                letter-spacing: 2.2px;
            }}
            QPushButton#magicApp:hover {{
                color: #04090f; background: {th.accent}; border-color: {th.accent};
            }}
            QLineEdit#magicInput {{
                background: rgba(0,0,0,0.45); color: {th.text};
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 22px; padding: 9px 20px; font-size: 13.5px;
                selection-background-color: {th.accent};
            }}
            QLineEdit#magicInput:focus {{ border-color: {th.accent}; }}
        """
