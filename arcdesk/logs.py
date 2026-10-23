"""Crash log — because a packaged .exe has nowhere to print.

When ArcDesk.exe is built with ``console=False`` there is no stdout and no
stderr: an exception at boot means the window simply never appears and the user
has nothing to report. That is the worst possible failure mode, so every
uncaught exception and every Qt warning is written to a small rotating file:

    %APPDATA%\\ArcDesk\\logs\\arcdesk.log      (or $ARCDESK_HOME/logs/)

Design rules:
  * never fatal — logging must not be able to crash the app
  * never grows: rotates at 256 KB, keeps one old file
  * never contains secrets: the formatter strips anything that looks like a key
  * reading it back is one function, so ``--doctor`` and the Settings tab can
    show "last errors" without opening a file manager
"""
from __future__ import annotations

import logging
import re
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import config

LOG_NAME = "arcdesk.log"
MAX_BYTES = 256 * 1024

# Every pattern is written as (keepsake-prefix)(secret): the scrubber replaces
# only the last group, so a line still reads "gsk_***" and stays diagnosable.
_SECRET_PATTERNS = (
    re.compile(r"(sk-)([A-Za-z0-9_\-]{8,})"),
    re.compile(r"(gsk_)([A-Za-z0-9_\-]{8,})"),
    re.compile(r"(AIza)([A-Za-z0-9_\-]{10,})"),
    re.compile(r"(?i)(api[_-]?key\"?\s*[:=]\s*\"?)([^\"\s,}]+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]{12,})"),
)


def log_dir() -> Path:
    d = config.data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_path() -> Path:
    return log_dir() / LOG_NAME


def _scrub(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub(lambda m: m.group(1) + "***", text)
    return text


class _ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = _scrub(str(record.msg))
            if record.args:
                record.args = tuple(_scrub(str(a)) for a in record.args) \
                    if isinstance(record.args, tuple) else record.args
        except Exception:
            pass
        return True


_installed = False


def install(level: int = logging.INFO) -> Path:
    """Attach the rotating file handler once. Safe to call from anywhere."""
    global _installed
    path = log_path()
    if _installed:
        return path
    try:
        root = logging.getLogger("arcdesk")
        root.setLevel(level)
        handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=1,
                                      encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        handler.addFilter(_ScrubFilter())
        root.addHandler(handler)

        def _hook(exc_type, exc, tb):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc, tb)
                return
            root.error("uncaught: %s", "".join(
                traceback.format_exception(exc_type, exc, tb))[-4000:])
            sys.__excepthook__(exc_type, exc, tb)

        sys.excepthook = _hook
        _installed = True
        root.info("── Arc Desk start · python %s · frozen=%s",
                  sys.version.split()[0], getattr(sys, "frozen", False))
    except Exception:
        pass
    return path


def install_qt(app=None) -> None:
    """Route Qt's own warnings into the same file (best effort)."""
    try:
        from PySide6.QtCore import qInstallMessageHandler
    except Exception:
        return
    logger = logging.getLogger("arcdesk.qt")

    def handler(mode, ctx, message):  # noqa: ANN001
        try:
            logger.warning("%s", _scrub(str(message)))
        except Exception:
            pass

    try:
        qInstallMessageHandler(handler)
    except Exception:
        pass


def tail(lines: int = 40) -> list[str]:
    try:
        with open(log_path(), "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()[-lines:]
    except Exception:
        return []


def errors(limit: int = 5) -> list[str]:
    return [ln for ln in tail(400) if " ERROR " in ln or " CRITICAL " in ln][-limit:]


def clear() -> bool:
    """Wipe the log from the Settings dialog. Returns True when it worked."""
    try:
        p = log_path()
        if p.exists():
            p.unlink()
        return True
    except Exception:
        return False
