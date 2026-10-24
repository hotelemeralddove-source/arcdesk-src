ARC DESK — FIX PACK 20
"Run #14 was green, and shipped an app that cannot open"
================================================================

WHAT I FOUND (from your Actions page, not from guessing)
--------------------------------------------------------
Run #14 "installer wont start" — completed successfully, 3m 20s.
Job 120846694082, every step "success".

Look at the step DURATIONS. That is where the lie is:

    run #13 "console"                 run #14 "installer wont start"
    ------------------------------    -------------------------------
    build the two executables
        10:02:11 -> 10:03:59              10:17:00 -> 10:17:02
        = 108 seconds  (worked)           = 2 SECONDS  (died instantly)
    fallback build
        0 seconds (skipped)               10:17:02 -> 10:18:16 = 74 s (IT built
                                          the exe you installed)
    zip + installer: success              success
    job: success                          success

So in run #14 the spec build failed in two seconds, the "fallback build, if the
spec was unhappy" step quietly built something else, and the installer packed it.

THE TWO-SECOND FAILURE, EXACTLY
-------------------------------
PyInstaller runs packaging/arcdesk.spec with a namespace of its own. I read
PyInstaller 6.22.3's source (PyInstaller/building/build_main.py):

    spec_namespace = { 'DISTPATH', 'HOMEPATH', 'SPEC', 'specnm', 'SPECPATH',
                       'WARNFILE', 'workpath', 'TOC', 'Analysis', 'BUNDLE',
                       'COLLECT', 'EXE', 'MERGE', 'PYZ', 'Tree', 'Splash',
                       'os' }

There is NO 'sys'. And my fix17 added:

    sys.path.insert(0, str(ROOT / "tools"))       <- NameError: name 'sys' is not defined
    _msvc = msvc_runtime_files(sys.base_prefix)

That is a 2-second crash. I proved it here by executing the real spec inside
that exact namespace:

    NameError (this is what breaks the build in 2 seconds): name 'sys' is not defined

With `import sys` added:

    [spec] runtime: no MSVC DLLs found next to this Python ...
    reached a later stage, so the namespace was fine

WHY YOUR SHORTCUT HAD THE WRONG ICON
------------------------------------
The fallback command was:

    python -m PyInstaller --noconfirm --clean --windowed --name ArcDesk \
        --collect-submodules arcdesk --distpath dist --workpath work2 run.py

No --icon  -> PyInstaller's default icon. That yellow-and-blue box on your
              desktop is PyInstaller's logo, not Arc Desk's.
No datas   -> no arc_icon, no TOOLS_PAGE.html, nothing the app expects.
No voice   -> no ArcDeskVoice.exe at all (the wake word could never work).
--windowed -> no console, so when it died at start-up it said nothing.

Installed, silent, dead. Exactly what you saw.

THE FIX — THREE PLACES, SO IT CANNOT HAPPEN AGAIN
-------------------------------------------------
1. packaging/arcdesk.spec
   `import sys` at the top, with a comment explaining that PyInstaller does not
   give it to you. This is the one-line fix for run #14.

2. .github/workflows/build-windows.yml  (rewritten)
   * libraries install strictly (no more "a missing wheel = a surprise later")
   * step 2: tools/preflight_win.py judges the machine in 5 s
   * step 3: the spec build has NO continue-on-error. If it fails, the build fails
   * step 4: verify the output is a WORKING APP, not a folder:
             ArcDesk.exe + ArcDeskVoice.exe + _internal + _internal\arcdesk\
             TOOLS_PAGE.html + shots\arc_icon.ico. Any miss = red
   * step 5: START the built exe on the runner (`ArcDesk.exe --doctor`), wait,
             then read %ARCDESK_HOME%\ArcDesk\logs\arcdesk.log. If there is no
             log, or a Traceback, the build FAILS. This is the step that would
             have caught run #14 — a frozen app that dies still leaves a log
   * step 6/7: zip, then the installer is REQUIRED (no more "best effort")
   * the run log is uploaded every time, pass or fail
   * the silent "fallback build" step is deleted

3. tests/test_spec_exec.py  (new, 7 sections)
   It executes the real spec inside PyInstaller's REAL namespace — read from
   PyInstaller's own source at test time and asserted against it — with
   Analysis/EXE/COLLECT/PYZ stubbed. It fails on NameError, and it also checks
   what the spec asked for: two exes, console=False, onedir, an icon that
   exists, the MSVC runtime, the runtime hook, the doctor script, the pages.
   This runs on Linux, so the bug is caught before you ever push.

VERIFIED
--------
  python tests/run_all.py        ->  72/72 passed in 92.1 s
  python tests/test_spec_exec.py ->  ALL PASS (7 sections)
  The old spec, in the real namespace      -> NameError: name 'sys' is not defined
  The fixed spec, same namespace           -> reaches the build classes

HOW TO FIX YOURS (easy, 3 steps, no command line)
-------------------------------------------------
  1. GitHub Desktop -> open arcdesk-src -> unzip this pack over the folder
     (the paths match: packaging/arcdesk.spec, .github/workflows/..., tests/...)
  2. Commit: "spec: import sys (fixes the 2-second build) + workflow verification"
  3. Push origin. The action runs by itself, about 4 minutes.

  Then, on your PC:
  4. Uninstall the broken Arc Desk first:
     Settings > Apps > Arc Desk > Uninstall   (answer NO to deleting the vault)
  5. Actions -> the newest green run -> Artifacts -> ArcDesk -> download BOTH
     files: ArcDeskSetup.exe and ArcDesk-portable.zip
  6. If you want it working in 20 seconds, without installing anything:
     unzip ArcDesk-portable.zip, open the folder, double-click ArcDesk.exe.
     The icon will now be Arc Desk's own, and ArcDeskVoice.exe will be there.

  If the run goes RED, send me the red step's name and the last 30 lines. A red
  build is the pipeline working — it stopped a broken exe from reaching you.

FILES IN THIS PACK
------------------
  packaging/arcdesk.spec                 import sys (+ the reason)
  .github/workflows/build-windows.yml    rewritten: verify, then ship
  tests/test_spec_exec.py                NEW: execute the spec the real way
  tests/test_windows_build.py            new section 7d: the workflow's rules
  CAPABILITIES.md README.md MACHI.md REEVAL.md CROSSCHECK.md
  SETUP_GITHUB.md                        counts 71 -> 72
  README-FIX20.txt                       this file
