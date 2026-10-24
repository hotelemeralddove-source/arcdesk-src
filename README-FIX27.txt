ARC DESK - FIX PACK 27
"Screen la ellam theriyanum, JARVIS nu sonna JARVIS, voice upload work aaganum."
================================================================================

WHAT YOU REPORTED (3 things, all fixed here)
--------------------------------------------
1. "even screen ah viitu veliya poiruku app size so enakku minimize pana, expand pana,
    screen size adjust panra mathithi, scroll pani all details ayum pakura mathiri"
2. "then submit panra mathiri option varNUM nu antha box varala"   <- the SAME bug
3. "nan kooda ARC nu sola vendam, JARVIS nu solanum"
4. "voice upload pana mudiyala"                                    <- and why

THE ONE BUG BEHIND 1 AND 2
--------------------------
Window geometry, measured:
    Voices dialog   minimum 640x660     a 1366x768 laptop at 125% scaling has
    Settings dialog minimum 640x560     only 1092x614 usable pixels
    main window     minimum 840x570     -> the Done/Save button was BELOW the screen
The button was there the whole time. It was just off the bottom edge, which is
indistinguishable from "there is no submit button".

WHAT IS NEW — arcdesk/widgets/fit.py
------------------------------------
Every window is now fitted to the screen it is opened on, measured with
QScreen.availableGeometry() instead of guessed:
  * fit_dialog()      never taller/wider than 90% of the usable area, centred, and the
                      minimum is clamped too (a minimum bigger than the screen is the bug)
  * scroll_body()     the body scrolls, the ACTION ROW (Done / Save / Start) is pinned
                      OUTSIDE the scroll — so the button that finishes the job is always
                      visible, on any laptop
  * clamp_to_screen() a window remembered from a 27-inch monitor is pulled back on screen
  * add_size_grip()   a frameless window can be dragged smaller (it could not be before)
Applied to: Voices, Settings (every tab scrolls now), Engines, Brain, Ears.

MAIN WINDOW CONTROLS (the ones you asked for by name)
-----------------------------------------------------
  –  minimise to the taskbar (the reactor keeps running)
  ▢  expand to fill the screen / back to a window
  ⌄  hide to the tray
  ◢  resize grip, bottom-right corner
  minimum size 840x570 -> 560x420, then clamped further if the display is smaller
New test: tests/test_fit.py runs every dialog against FOUR fake screens — 1920x1080,
1366x768 at 100%, 1366x768 at 125% (1092x614: the one that broke), and 1280x720 — and
asserts the dialog fits, scrolls, and that Done/Save is on screen each time. All pass.

IT CALLS ITSELF JARVIS NOW — arcdesk/identity.py
------------------------------------------------
One setting, used everywhere:
    DEFAULT_NAME = "JARVIS"      identity.name(cfg)   identity.intro(cfg)
    cfg["ai"]["name"] overrides it (blank falls back — never a nameless introduction)
  * "ASK ARC" -> "ASK JARVIS" on the main window
  * the persona prompt says: You are {name}. Say "I am {name}" — never "I am ARC".
  * 191 sentences across 57 files that used to say ARC now say JARVIS
  * "ARC DESK" (the header, the installer) and "ARC Lite" stay: one is the product you
    installed, the other is who answers when you talk to it.
New test: tests/test_name.py.

WHY THE VOICE UPLOAD DID NOTHING (found by doing it, not by reading it)
----------------------------------------------------------------------
I ran the real functions:
    add_command(wav) -> {'ok': False, 'message': 'the speaker-embedding model is not
                         downloaded yet (`python tools/voice_setup.py lock-model`)'}
    add_reply(wav)   -> {'ok': False, 'message': 'only 3.1 s of speech found — I need at
                         least 4 s, ideally 12 s'}
Two honest refusals — and both were invisible, because they were printed inside a small
log box at the bottom of a dialog that was taller than the screen. Fixes:
  * a one-click button IN the Voices window: "Download the voice-lock model (30 MB)…",
    downloading in the background and reporting in the same window. No terminal, ever.
  * the clip requirement is written ABOVE the button, before you pick a file:
    "Use a 10-20 second clip of one person talking, no music. 4 s is the minimum."
  * a refusal now opens a message box. A refusal inside a scroll area is not a message.

STARTING FELT SLOW
------------------
Measured here: 0.1 s from launch to a shown window (source build). On your PC the time
goes into loading DLLs from disk and antivirus scanning them, which cannot be made
instant — but silence CAN be removed. So a small card now appears immediately
("ARC DESK / starting JARVIS…"), disappears when the real window is up, and can never
outlive a failure (8-second ceiling). The app also logs its own start time:
    BOOT · 0.1 s from the double-click to the window
If that number is large on your laptop, it is in the log and in ArcDeskDiag's report.

GATES
-----
  python tests/run_all.py      74/74 passed in 110.7 s   (2 new: test_fit, test_name)
  python tests/test_docs.py    PASS
  python tools/gen_tools_doc.py --check   88 tools, 0 mismatch
  python tools/batlint.py      16/16 batch files clean

Apply: unzip over the repo, GitHub Desktop > commit > Push. Then install from the new run.
