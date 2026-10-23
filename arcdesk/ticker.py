"""One timer to drive every animation in the app.

This is the single most important file for keeping CPU/GPU cost down.
Instead of N widgets each owning a QTimer at their own rate, there is one
shared QTimer. Widgets only repaint when they are visible, and the whole
ticker drops to 10 fps in Gaming mode or stops entirely when animations
are paused.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal


class FrameTicker(QObject):
    tick = Signal(float)  # seconds since previous tick (clamped)

    def __init__(self) -> None:
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._emit)
        self._fps = 30
        self._paused = False
        self._last = time.perf_counter()
        self._apply()

    # -- control ---------------------------------------------------------
    def set_fps(self, fps: int) -> None:
        fps = max(1, min(120, int(fps)))
        if fps == self._fps:
            return
        self._fps = fps
        self._apply()

    def set_paused(self, paused: bool) -> None:
        if paused == self._paused:
            return
        self._paused = paused
        self._apply()

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def fps(self) -> int:
        return 0 if self._paused else self._fps

    # -- internals -------------------------------------------------------
    def _apply(self) -> None:
        if self._paused:
            self._timer.stop()
            return
        self._timer.setInterval(max(8, int(1000 / self._fps)))
        if not self._timer.isActive():
            self._last = time.perf_counter()
            self._timer.start()

    def _emit(self) -> None:
        now = time.perf_counter()
        dt = now - self._last
        self._last = now
        # Clamp: after sleep/resume or a stall, never hand widgets a 4-second dt.
        self.tick.emit(min(dt, 0.1))


_ticker: FrameTicker | None = None


def ticker() -> FrameTicker:
    global _ticker
    if _ticker is None:
        _ticker = FrameTicker()
    return _ticker
