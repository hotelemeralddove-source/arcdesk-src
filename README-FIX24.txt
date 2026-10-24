ARC DESK - FIX PACK 24
"Two Arc Desk windows at once, and none of them on screen."
==============================================================

WHAT THE USER'S DIAGNOSTIC PROVED (ArcDeskDiag.txt, section 6)
--------------------------------------------------------------
    ArcDesk.exe   22016  Console  8  1,03,872 K
    ArcDesk.exe   23360  Console  8  1,30,876 K

TWO copies of the app were running, ~100 MB each — so the exe builds, starts, loads
PySide6 and lives. The runtime, the MSVC DLLs and the packaged Python were all fine.
What was broken was VISIBILITY, and the single-instance lock that should have made the
second copy impossible.

THE TWO BUGS, both fixed here
-----------------------------
1. TWO COPIES. arcdesk/instance.py set SO_REUSEADDR, which on Windows means the
   opposite of what it means on Linux: Windows lets a second socket bind an address
   that is already in use, so both processes believed they were the only one — two
   windows, two tray icons, two microphone listeners. Now Windows gets
   SO_EXCLUSIVEADDRUSE (set before bind), which makes a second copy lose the bind,
   forward {"event":"show"} to the first and exit. Proven by
   tests/test_app_lifecycle.py section 7, which checks both platform branches and does
   a real double-acquire on the current machine.

2. NO WINDOW. "start hidden" defaulted to true and --shadow (the boot flag) was saved
   into settings.json, so a click on the icon started a process that showed nothing.
   The installer's shortcuts now pass --show, --shadow is a per-launch flag that
   config.save() strips, a one-time migration corrects old settings files (unless the
   person ticked the box themselves), and run.py logs its decision:
       BOOT · the window is shown
       BOOT · handles: tray=yes, hotkeys=yes, stealth=off

ALSO IN HERE
------------
  * FIX-OPEN.bat — the click-only repair that needs no rebuild at all
  * ArcDeskDiag.bat — now also prints the app's last 60 log lines and the exe size
  * step 4b in the workflow: the exe's icon is checked byte-for-byte
  * step 5 waits for the exe to exit and requires the doctor's RESULT line
  * no sys.path tricks anywhere (that was run #15's six-second build)

GATES
-----
  python tests/run_all.py          72/72 passed in 110.6 s
  python tests/test_app_lifecycle.py   includes the Windows lock branch
  python tools/batlint.py          16/16 batch files clean
