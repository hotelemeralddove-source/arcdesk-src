"""Arc Desk launcher.

    python run.py                      # normal boot
    python run.py --mode gaming        # boot straight into a mode
    python run.py --screenshot out.png # render a still (dev/QA helper)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QSystemTrayIcon

from arcdesk import __version__, config
from arcdesk.theme import MODE_ORDER
from arcdesk.widgets.window import MainWindow


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    ap = argparse.ArgumentParser(prog="arcdesk", description="Arc Desk — Phase 1")
    ap.add_argument("--mode", choices=MODE_ORDER, help="start in this power mode")
    ap.add_argument("--screenshot", metavar="PNG", help="save a still frame and exit")
    ap.add_argument("--advance", type=float, default=2.6, help="seconds to fast-forward")
    ap.add_argument("--no-tray", action="store_true")
    ap.add_argument("--console", action="store_true", help="open the ARC console")
    ap.add_argument("--download-voice-model", dest="download_voice_model",
                    action="store_true",
                    help="download the speech model (40 MB) and the speaker model (30 MB), "
                         "then exit — the installer offers this")
    ap.add_argument("--ask", metavar="TEXT", help="send one prompt and print ARC's answer")
    ap.add_argument("--demo-chat", action="store_true", help="seed a sample conversation")
    ap.add_argument("--shadow", action="store_true",
                    help="start hidden: no window, no tray icon (boot with Windows)")
    ap.add_argument("--show", action="store_true", help="force the window visible")
    ap.add_argument("--palette", action="store_true", help="open the command palette")
    ap.add_argument("--awaken-shot", metavar="PNG",
                    help="render the awakening animation mid-frame and exit")
    ap.add_argument("--palette-shot", metavar="PNG", help="render the palette and exit")
    ap.add_argument("--magic-shot", metavar="PNG",
                    help="render the magic-mode screen and exit")
    ap.add_argument("--charms-shot", metavar="PNG",
                    help="render the charm overlay over a mock desktop and exit")
    ap.add_argument("--doctor", action="store_true",
                    help="check this install and exit (python run.py --doctor)")
    ap.add_argument("--no-instance", action="store_true",
                    help="allow a second copy (dev/screenshot runs)")
    ap.add_argument("--version", action="version", version=f"Arc Desk {__version__}")
    args, qt_args = ap.parse_known_args(argv[1:])

    from arcdesk import logs
    logs.install()

    if args.doctor:
        # In a frozen build __file__ points into the temp/install internals, so the
        # tools folder has to be found from the bundle root (PyInstaller's _MEIPASS).
        base = Path(getattr(sys, "_MEIPASS", "") or Path(__file__).resolve().parent)
        sys.path.insert(0, str(base / "tools"))
        import doctor
        return doctor.run()

    # Bundled tools (ffmpeg, node) live inside the install. Adding them to THIS process's
    # PATH is what removes the "set your path" step for the user — and it touches nothing
    # outside this process, so uninstalling leaves Windows exactly as it was.
    from arcdesk import paths as _paths
    _runtime = _paths.activate_runtime()
    if _runtime:
        # say it once, in the log, so "is ffmpeg included?" has an answer that is not a guess
        print("bundled runtime on PATH: " + ", ".join(_runtime), flush=True)

    cfg = config.load()
    if args.mode:
        cfg["mode"] = args.mode
    if args.shadow:
        cfg.setdefault("shadow", {})["enabled"] = True
    if args.show:
        cfg["_force_show"] = True

    # One Arc Desk at a time. A second launch does not open a second reactor —
    # it tells the first one to wake up, which is what the user expects from
    # saying "Hey Jarvis" twice.
    dev_run = bool(args.screenshot or args.ask or args.demo_chat or args.palette_shot
                   or args.magic_shot or args.awaken_shot or args.charms_shot)
    inst = None
    if not (args.no_instance or dev_run):
        from arcdesk.instance import Instance
        inst = Instance(cfg)
        if not inst.acquire():
            inst = None
            print("Arc Desk is already running — bringing it to the front.")
            return 0

    app = QApplication([argv[0]] + qt_args)
    app.setApplicationName("Arc Desk")
    app.setApplicationDisplayName("Arc Desk")
    app.setOrganizationName("ArcDesk")
    app.setQuitOnLastWindowClosed(False)   # we live in the tray

    # ---- close cleanly when something asks us to ---------------------------
    # Ctrl+C in a console, `taskkill` (without /F), a service stop or a stopped build
    # all arrive as a signal. Unhandled, Python prints a KeyboardInterrupt traceback
    # and skips the instance-lock release and the magic-mode journal restore, so the
    # *next* launch would believe Arc Desk is already running.
    #
    # This is installed right after the QApplication and BEFORE the first-run wizard,
    # because that wizard runs its own nested event loop — the first version of this
    # code sat after it and therefore could never answer a signal sent while the user
    # was still reading the setup cards (measured: exit -15, no clean shutdown).
    #
    # A Python signal handler must not touch Qt directly, so it only sets a flag and a
    # small timer in the GUI thread performs the quit.
    import signal as _signal

    stop_request: dict[str, int] = {"signal": 0}

    def _ask_to_quit(signum, _frame) -> None:
        stop_request["signal"] = int(signum)

    for _sig in ("SIGINT", "SIGTERM", "SIGBREAK", "SIGHUP"):
        _name = getattr(_signal, _sig, None)
        if _name is not None:
            try:
                _signal.signal(_name, _ask_to_quit)
            except (ValueError, OSError):
                pass

    def _watch_for_stop() -> None:
        if not stop_request["signal"]:
            return
        # Any dialog still on screen is rejected explicitly, which is what lets the
        # setup loop below fall out immediately. Without it, a stop signal sent while
        # the first-run wizard was open left the process alive for another 12 s and it
        # had to be killed (measured in the sandbox, before the loop was rewritten).
        for widget in app.topLevelWidgets():
            try:
                if isinstance(widget, QDialog) and widget.isVisible():
                    widget.reject()
            except Exception:
                pass
        app.quit()

    _heartbeat = QTimer(app)
    _heartbeat.setInterval(200)
    _heartbeat.timeout.connect(_watch_for_stop)
    _heartbeat.start()


    logs.install_qt()
    win = MainWindow(cfg)
    if inst is not None:
        # emit, don't call: the lock socket is served by a plain thread, and Qt
        # widgets may only be touched from the GUI thread. A signal hops over.
        win.summon_requested.connect(win.summon)
        inst.on_summon = win.summon_requested.emit
        app.aboutToQuit.connect(inst.release)

    from arcdesk.tray import ArcTray, reactor_icon
    win.setWindowIcon(reactor_icon(cfg["mode"]))
    tray = None
    hidden_boot = (args.shadow or win.shadow) and not args.show
    if hidden_boot:
        win.hide()
    want_tray = bool(cfg.get("shadow", {}).get("tray", True)) and not args.no_tray
    if want_tray and QSystemTrayIcon.isSystemTrayAvailable():
        tray = ArcTray(win)
        tray.show()
        app.setProperty("arc_tray", True)

    if not hidden_boot:
        win.show()

    if getattr(args, "download_voice_model", False):
        # The installer offers this as a post-install tick: without the 40 MB speech
        # model and the 30 MB speaker model, "hey jarvis" cannot work on a fresh
        # machine — so the download is one visible step, not a mystery failure later.
        import subprocess as _sp
        from arcdesk import paths as _paths
        from arcdesk import voiceid as _voiceid
        ok_all = True
        print("[1/2] speech model (Vosk, ~40 MB) …")
        try:
            cmd, kwargs = _paths.daemon_command(8765, "hey jarvis", "auto", "bye jarvis",
                                                extra=["--download-model"])
            done = _sp.run(cmd, timeout=1800, **kwargs)
            ok_all &= done.returncode == 0
        except Exception as exc:                                # noqa: BLE001
            ok_all = False
            print(f"      failed: {type(exc).__name__}: {exc}")
        print("[2/2] speaker model (voice lock, ~30 MB) …")
        got = _voiceid.download_model()
        print("      " + got["message"])
        ok_all &= bool(got["ok"])
        print("done." if ok_all else "some downloads failed — Settings → Voice can retry.")
        return 0 if ok_all else 1

    if args.console:
        win.toggle_console(True)

    # first run: one card, three decisions, the evidence next to each one
    if cfg.get("first_run", True) and not (args.screenshot or args.demo_chat or args.ask):
        try:
            from arcdesk.ai import backends
            from arcdesk.widgets.welcome import WelcomeDialog
            engines = [d.describe() for d in backends.probe()]
            dlg = WelcomeDialog(cfg, win.voice, engines, parent=win)
            # Not dlg.exec(): a nested event loop of its own cannot be left cleanly when
            # a stop signal arrives mid-setup (measured: SIGBUS on teardown). Pumping the
            # main loop keeps the dialog modal in practice and makes a stop request just
            # fall out of the loop.
            dlg.show()
            while dlg.isVisible() and not stop_request["signal"]:
                app.processEvents()
                time.sleep(0.01)
            result = getattr(dlg, "setup_result", None)
            if result:
                # say what was actually set, in the console, where it can be read again
                from arcdesk import firstrun
                for line in firstrun.summary(result).splitlines():
                    win.console.add_note(line)
                # ...and make the choice TRUE right now: choosing "voice" means the ears
                # start in this same session, not after the next login.
                if cfg.get("wake", {}).get("enabled"):
                    win._set_wake_pill(True)
                    win._start_wake()
                else:
                    win._stop_wake()
        except Exception:
            pass

    # "which file mentions X" only works once something has been read. Do it once, in
    # the background, so the window is never blocked by somebody's 4,000 PDFs.
    if cfg.get("docs", {}).get("index_on_start") and not (args.screenshot or args.ask):
        from arcdesk import docs_worker
        docs_worker.start(win)

    if args.demo_chat or args.ask:
        win.toggle_console(True)
        if args.demo_chat:
            c = win.console
            c.add_user("what is my cpu doing, and open notepad")
            c.add_tool("system_report", "{}",
                       "cpu 18% (8 threads); ram 61% used, 3.1 GB free of 7.9 GB; "
                       "disk 74% used, 61 GB free; battery 88% charging")
            c.add_tool("open_app", '{"app": "notepad"}', "launched notepad")
            c.add_arc("CPU is sitting at eighteen percent and RAM at sixty one. "
                      "Notepad is open. Nothing is choking the machine right now.")
        if args.ask:
            import PySide6.QtCore as _qc

            answer: dict[str, str] = {}
            win.console.add_user(args.ask)
            win.agent.reply.connect(lambda t: (answer.setdefault("text", t),))
            win.agent.error.connect(lambda e: answer.setdefault("error", e))
            loop = _qc.QEventLoop()
            win.agent.reply.connect(lambda *_: loop.quit())
            win.agent.error.connect(lambda *_: loop.quit())
            _qc.QTimer.singleShot(60_000, loop.quit)
            win.agent.ask(args.ask)
            loop.exec()
            for _ in range(6):
                app.processEvents()
            if answer.get("error"):
                print("[error]", answer["error"])
            print("[ARC]", answer.get("text", "(no answer)"))
            return 0 if answer.get("text") else 2

    if args.awaken_shot:
        from arcdesk.widgets.awakening import Awakening
        aw = Awakening(win.theme, "ARC // ONLINE")
        aw.show()
        for _ in range(4):
            app.processEvents()
        aw.advance(1.05)
        for _ in range(4):
            app.processEvents()
        ok = aw.grab().save(args.awaken_shot)
        print(("saved " if ok else "failed to save ") + args.awaken_shot)
        return 0 if ok else 1

    if args.palette_shot:
        win.palette.set_theme(win.theme)
        win.palette.set_brain(win.agent.describe())
        win.palette.popup()
        win.palette.input.setText("open google")
        win.palette.show_line("› open google")
        win.palette.show_line("launched https://www.google.com")
        for _ in range(6):
            app.processEvents()
        ok = win.palette.grab().save(args.palette_shot)
        print(("saved " if ok else "failed to save ") + args.palette_shot)
        return 0 if ok else 1

    if args.magic_shot:
        win._magic_screen = win._magic_screen or __import__(
            "arcdesk.widgets.magicscreen", fromlist=["MagicScreen"]).MagicScreen(
            win.theme, "bye jarvis")
        ms = win._magic_screen
        ms.resize(1440, 900)
        ms.show()
        for _ in range(4):
            app.processEvents()
        ms.advance(2.4)
        ms.set_status("MAGIC MODE ACTIVE - ASK ME ANYTHING")
        for _ in range(6):
            app.processEvents()
        ok = ms.grab().save(args.magic_shot)
        print(("saved " if ok else "failed to save ") + args.magic_shot)
        return 0 if ok else 1

    if args.charms_shot:
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
        win.show_charms(True)
        win.overlay.resize(1280, 720)
        win.overlay.show()
        for _ in range(4):
            app.processEvents()
        win.overlay.advance(2.2)
        for _ in range(4):
            app.processEvents()

        # composite over a mock Windows desktop so the shot reads properly
        canvas = QPixmap(1280, 720)
        canvas.fill(QColor("#0b1a2b"))
        cp = QPainter(canvas)
        cp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        g = QLinearGradient(0, 0, 1280, 720)
        g.setColorAt(0.0, QColor("#0d2137"))
        g.setColorAt(0.55, QColor("#123049"))
        g.setColorAt(1.0, QColor("#0a1622"))
        cp.fillRect(0, 0, 1280, 720, g)
        cp.setPen(QColor(255, 255, 255, 28))
        for i in range(9):          # pretend desktop icons
            cp.setBrush(QColor(255, 255, 255, 22))
            cp.drawRoundedRect(QRectF(34, 34 + i * 88, 48, 40), 6, 6)
        cp.setBrush(QColor(10, 16, 24, 235))   # pretend taskbar
        cp.setPen(QColor(255, 255, 255, 18))
        cp.drawRect(QRectF(0, 676, 1280, 44))
        cp.end()
        overlay_pix = win.overlay.grab()
        cp = QPainter(canvas)
        cp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        cp.drawPixmap(0, 0, overlay_pix)
        cp.end()
        ok = canvas.save(args.charms_shot)
        print(("saved " if ok else "failed to save ") + args.charms_shot)
        return 0 if ok else 1

    if args.palette:
        win.palette.popup()

    if args.screenshot:
        for _ in range(8):
            app.processEvents()
        win.advance(args.advance)
        for _ in range(4):
            app.processEvents()
        ok = win.grab().save(args.screenshot)
        print(("saved " if ok else "failed to save ") + args.screenshot)
        return 0 if ok else 1

    if stop_request["signal"]:
        # We were asked to stop before the main loop was ever entered (typically while
        # the first-run wizard was still on screen). Leave nothing holding the lock.
        #
        # Deliberately no win.close() here: the dialog had just been rejected from inside
        # a timer callback, and closing the window as well crashed the interpreter on the
        # way out (measured: SIGBUS, exit 135, three times out of three). Returning is
        # enough — Qt tears the rest down itself and the instance lock is a socket, so it
        # is released by the OS even if a later teardown were to fault.
        _heartbeat.stop()
        print("Arc Desk closed cleanly.", flush=True)
        return 0

    rc = app.exec()
    _heartbeat.stop()
    if tray is not None:
        tray.hide()
    if stop_request["signal"]:
        print("Arc Desk closed cleanly.", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
