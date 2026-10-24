ARC DESK — FIX PACK 16
"No more command prompt windows opening behind the app"
================================================================

WHAT YOU SAW
------------
"neraya transparent command prompt open aaitae iruku arcdesk ah run pana"

WHAT WAS HAPPENING
------------------
ArcDesk is a WINDOWLESS program on purpose: no black box behind the interface
(console=False in the exe, pythonw.exe when run from source).

That is the whole cause. A windowless parent hands its children no console, and
on Windows a console program started without a console GETS A BRAND-NEW ONE —
visible, black, there for a moment, gone.

So every one of these popped a command prompt:
  * every spoken sentence      (PowerShell + SAPI)
  * every screen read / OCR    (PowerShell, tesseract)
  * every video/audio clip     (ffmpeg, ffprobe)
  * every wake-daemon restart  (python arc_daemon.py)
  * every local-model start    (llama.cpp / ollama)
  * every UI Automation query

Say five sentences, watch five windows open. Leave it running and they keep
opening. `-WindowStyle Hidden` did NOT fix it: PowerShell creates and shows the
console first, then applies the style.

THE FIX (in two layers)
-----------------------
1. `arcdesk/quiet.py` — one wrapper, and 95 spawn sites in 24 modules go through
   it. On Windows every child gets CREATE_NO_WINDOW (+ SW_HIDE STARTUPINFO).
   `start_new_session=True` is translated to DETACHED_PROCESS |
   CREATE_NEW_PROCESS_GROUP, because the POSIX name raises ValueError on Windows.
   On Linux/macOS nothing changes: the flags are dropped, nothing breaks.

2. `ArcDesk.pyw` — double-click this instead of a .bat, and Windows runs it with
   pythonw.exe, so there is no console behind the app at all.
   It also fixes a trap: under pythonw.exe `sys.stdout` is None, so the first
   print() in run.py would kill the app before it drew anything.
   `arcdesk/logs.py` now points both streams at
   %APPDATA%\ArcDesk\logs\arcdesk.log (rotating at 512 KB, API keys scrubbed)

VERIFIED
--------
  python tests/run_all.py   ->  70/70 passed in 81.9 s · "everything passes."
  python tests/test_quiet.py (new, 8 sections):
      * the flag maths, including the Windows branch
      * a real child still answers, still fails, check=True still raises
      * shell=True still works
      * ZERO direct subprocess calls left in runtime code (source scan — a new
        one fails the build instead of appearing on your screen)
      * the wake daemon is spawned detached and silent
      * a real windowless launch of ArcDesk.pyw --help exits 0 and its output
        lands in the log, not in a lost buffer
      * the spec stays console=False

WHAT I COULD NOT SEE FROM HERE
------------------------------
This sandbox is Linux: there is no console window to watch appear, so I verified
the flag maths, the source scan and the windowless launch — not the visual flash
itself. On your laptop the check is simple.

  Double-click ArcDesk.pyw, say five things to it, take a screenshot, ask it to
  draw something. If any black window appears, tell me and I will follow it.

FILES IN THIS PACK
------------------
  arcdesk/quiet.py              NEW  the silent spawn layer
  arcdesk/logs.py               rotating log + windowless stdout/stderr (rebuilt)
  ArcDesk.pyw                   NEW  double-click launcher, no console
  24 runtime modules            every subprocess call routed through quiet
  arcdesk/paths.py              the wake daemon: silent AND detached
  tools/doctor.py               two new rows: "Silent spawns", "Console output"
  tests/test_quiet.py           NEW  8 sections
  tests/test_app_lifecycle.py   patches quiet.popen (the seam moved)
  COMMANDS.md                   new section 0d
  CAPABILITIES.md README.md MACHI.md REEVAL.md CROSSCHECK.md SETUP_GITHUB.md
  WHATS_INCLUDED.md             regenerated
  README-FIX16.txt              this file
