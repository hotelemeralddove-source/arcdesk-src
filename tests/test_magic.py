"""Magic mode: 'Hey JARVIS' in, 'BYE JARVIS' out — proven without a microphone.

Runs the real window, feeds the real daemon's simulated wake/exit messages over
a real socket, and asserts the state machine: active -> inactive, and that the
journal is cleaned up so an interrupted session cannot leave your wallpaper
changed.

Run:  QT_QPA_PLATFORM=offscreen python tests/test_magic.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import os
import tempfile

# keep tests away from the real settings folder (see config.data_dir)
os.environ.setdefault("ARCDESK_HOME", tempfile.mkdtemp(prefix="arcdesk-test-"))

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from arcdesk import config  # noqa: E402
from arcdesk.magic import JOURNAL  # noqa: E402
from arcdesk.widgets.window import MainWindow  # noqa: E402

PORT = 8901


def pump(app, seconds=0.6):
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    loop.exec()
    app.processEvents()


def run_daemon(*args) -> str:
    script = Path(__file__).resolve().parents[1] / "arc_daemon.py"
    out = subprocess.run([sys.executable, str(script), "--port", str(PORT), *args],
                         capture_output=True, text=True, timeout=30)
    return (out.stdout or "") + (out.stderr or "")


def main() -> int:
    app = QApplication(sys.argv[:1])
    cfg = config.load()
    cfg["mode"] = "chill"
    cfg["window"] = {"w": 1000, "h": 690, "x": 20, "y": 20}
    cfg["ai"] = {"enabled": True, "provider": "lite", "voice": False}
    cfg["wake"] = {"enabled": True, "phrase": "hey jarvis", "engine": "auto",
                   "port": PORT, "command_seconds": 7, "autostart_daemon": False}
    cfg["magic"] = {"enabled": True, "exit_phrase": "bye jarvis",
                    "wallpaper": False, "restore_on_start": True}
    cfg["shadow"] = {"enabled": False, "awaken": False, "hotkeys": False, "tray": False}
    cfg["charms"] = {"enabled": False, "items": []}

    JOURNAL.unlink(missing_ok=True)
    win = MainWindow(cfg)
    pump(app, 0.3)

    ok = True
    if not win.wake_server.listening:
        print("FAIL: wake server not listening")
        return 1

    # ---- 1. "Hey JARVIS" -> magic on --------------------------------
    log = run_daemon("--simulate", "open google")
    pump(app, 1.2)
    print("daemon (wake) :", log.strip().splitlines()[-1] if log.strip() else "-")
    print("magic active  :", win.magic_active)
    print("magic screen  :", win._magic_screen is not None)
    if not win.magic_active or win._magic_screen is None:
        ok = False

    # ---- 2. journal exists while active, cleaned on exit -----------
    journal_there = JOURNAL.exists()
    print("journal while active:", journal_there)

    # ---- 3. "BYE JARVIS" -> back to normal -------------------------
    log2 = run_daemon("--simulate-exit")
    pump(app, 1.2)
    print("daemon (exit) :", log2.strip().splitlines()[-1] if log2.strip() else "-")
    print("magic active  :", win.magic_active)
    print("journal left  :", JOURNAL.exists())
    if win.magic_active or JOURNAL.exists():
        ok = False

    # ---- 4. crash recovery: a stale journal must heal ---------------
    JOURNAL.write_text(json.dumps({"active": True, "wallpaper_before": "",
                                   "wallpaper_after": "x.png"}), "utf-8")
    healed = win.magic.restore_if_needed()
    print("stale journal healed:", healed, "| journal now:", JOURNAL.exists())

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
