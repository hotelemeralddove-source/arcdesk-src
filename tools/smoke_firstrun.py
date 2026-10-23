#!/usr/bin/env python3
"""Start the real entry point the way Windows will, and watch what it does.

    python tools/smoke_firstrun.py                 # run.py --shadow
    python tools/smoke_firstrun.py --show          # run.py --show
    python tools/smoke_firstrun.py --seconds 10

Why this exists: every other test imports modules directly, so nothing proved that
`python run.py --shadow` — the exact command the autostart entry writes — gets from
"python starts" to "window exists" without a traceback. That gap is where a packaged
app usually dies (a missing data file, an import that only happens on first run).

What it checks, all of it observed rather than assumed:
  * the process is still alive after N seconds (it did not crash on startup)
  * it wrote a settings file in a throw-away ARCDESK_HOME
  * its output contains no Traceback
  * it exits within a few seconds of being asked (Ctrl+Alt+Q / SIGTERM path)

What it cannot check here: that a window actually appears on a real screen. In this
sandbox Qt runs offscreen, so the honest claim is "it boots", not "it looks right".
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ok = True


def check(label: str, got, want=True) -> None:
    global ok
    good = got == want
    print(f"   {'OK  ' if good else 'FAIL'} {label:<58} {str(got)[:34]!r}")
    ok &= bool(good)


def main(argv: list[str]) -> int:
    flag = "--show" if "--show" in argv else "--shadow"
    extra = [a for a in argv if a in ("--no-instance", "--no-tray")]
    seconds = 8.0
    if "--seconds" in argv:
        seconds = float(argv[argv.index("--seconds") + 1])

    home = Path(tempfile.mkdtemp(prefix="arcdesk-firstrun-"))
    env = dict(os.environ)
    env["ARCDESK_HOME"] = str(home)
    env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "offscreen")
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("ARCDESK_TEST", None)

    print(f"ARC DESK · first-run smoke  (run.py {flag})")
    print("=" * 70)
    print(f"  settings folder: {home}")

    started = time.time()
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "run.py"), flag, *extra],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", start_new_session=True,
    )
    alive_at_check = False
    try:
        deadline = started + seconds
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            time.sleep(0.25)
        alive_at_check = proc.poll() is None
    finally:
        boot_seconds = time.time() - started
        if proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            out = proc.communicate(timeout=12)[0] or ""
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            out = (proc.communicate()[0] or "") + "\n<had to be force-killed>"

    already = "already running" in out.lower()
    if already and "--no-instance" not in extra:
        print("   SKIP another Arc Desk holds the instance lock, so this run "
              "correctly forwarded and quit.")
        print("        Re-run with --no-instance for an isolated boot.")
        check("the second launch refused to open a second window", True)
        return 0
    check(f"still running after {seconds:.0f}s (it did not crash)", alive_at_check)
    code = proc.returncode
    check("it shut down cleanly when asked (exit 0)", code, 0)
    check("it said so on the way out", "closed cleanly" in out)
    check("no Traceback in its output", "Traceback" not in out)
    files = sorted(p.name for p in home.rglob("*") if p.is_file())
    check("a settings file was created", any(n.startswith(("settings", "config"))
                                             for n in files) or "settings.json" in files)
    check("it wrote inside the throw-away folder", bool(files))
    print(f"  files: {', '.join(files[:8]) or '(none)'}")
    check("boot was not absurdly slow", boot_seconds < seconds + 6)
    print(f"  boot wall time: {boot_seconds:.1f}s (includes the wait, not a measurement)")

    interesting = [ln for ln in out.splitlines()
                   if any(k in ln.lower() for k in ("error", "warn", "fail", "traceback"))]
    if interesting:
        print("  notes from its own output:")
        for line in interesting[:6]:
            print("    ·", line.strip()[:110])
    else:
        print("  it printed nothing alarming.")

    print("=" * 70)
    print("UNVERIFIED here: that the window looks right on a real screen — this "
          "sandbox has no display, Qt runs offscreen.")
    print("RESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
