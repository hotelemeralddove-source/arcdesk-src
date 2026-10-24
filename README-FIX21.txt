ARC DESK — FIX PACK 21
"Run #15: the 6-second build. Found it, fixed it, proved it."
================================================================

WHAT THE RUN PAGE SAYS (and what it hides)
------------------------------------------
Run #15 "spec: import sys + workflow verification" - FAILED, 1m 13s.
Only one step was red:

    3. build both executables from the spec    FAILED
       started 10:55:35  ->  failed 10:55:41     = 6 SECONDS

A real build takes 75-110 seconds. Six seconds means the spec never started
building. Everything after it was skipped (correctly - that is the new
pipeline doing its job: it refused to zip a broken exe).

THE REAL CAUSE (reproduced here, not guessed)
---------------------------------------------
My fix20 moved the MSVC-runtime helper into the spec with:

    sys.path.insert(0, str(ROOT / "tools"))
    from preflight_win import msvc_runtime_files

That puts `tools/` FIRST on Python's import path - and `tools/` contains
`tools/packaging.py`, OUR checker script. PyInstaller itself does:

    import packaging.requirements        (PyInstaller/utils/hooks/__init__.py:22)

So `packaging` resolved to `tools/packaging.py` (a module, not a package), and
PyInstaller's isolated build subprocess died with:

    ModuleNotFoundError: No module named 'packaging.requirements';
    'packaging' is not a package

I found it by instrumenting PyInstaller's own child process here. The line that
gave it away:

    DIAG packaging in modules=<module 'packaging' from '/home/user/arcdesk/tools/packaging.py'>

This is a general Python trap, not a PyInstaller quirk: a file named
`packaging.py` in a folder you put on sys.path wins over the pip package.

THE FIX
-------
1. packaging/arcdesk.spec - load the helper BY FILE, never by path insertion:

       import importlib.util as _ilu
       _pf_spec = _ilu.spec_from_file_location("_arc_preflight",
                                               ROOT / "tools" / "preflight_win.py")
       _pf = _ilu.module_from_spec(_pf_spec)
       _pf_spec.loader.exec_module(_pf)
       _msvc = _pf.msvc_runtime_files(sys.base_prefix)

   Zero sys.path side effects, so nothing can be shadowed.

2. run.py --doctor - the same trap existed there (`sys.path.insert(0, tools)`
   to reach doctor.py). Now loaded by file path too.

3. tools/preflight_win.py - NEW CHECK "Shadowing". It finds any repo file or
   folder whose name collides with an importable module, and:
       * FAILS the build when something actually puts that folder on sys.path
         ("this is the 6-second build, exactly")
       * says "latent only" when it does not (so a good build is not blocked)

4. tests/test_spec_exec.py - three new assertions that make this impossible to
   reintroduce: the spec contains NO sys.path.insert; `import packaging.requirements`
   still works after the spec has run; and the preflight's shadowing check really
   fails when armed (proven with a purpose-built fake tree).

5. .github/workflows/build-windows.yml - step 5 now WAITS for the exe to exit
   (WaitForExit(180000)) and requires the doctor's "RESULT:" line. Before it broke
   out of its wait loop on the app's own start-up line, which could read the log
   too early.

6. arcdesk/quiet.py + tools/doctor.py - the doctor no longer reports a false
   "[FAIL] Silent spawns" inside a packaged build (where there are no .py files
   to scan). It now says "23 of 23 ... (compiled build)".

VERIFIED — the strongest evidence so far
----------------------------------------
A FULL PyInstaller build now runs here and completes (75 s):

    [spec] ears: bundling vosk
    [spec] bundling arcdesk/TOOLS_PAGE.html
    [spec] runtime: no MSVC DLLs found next to this Python ...
    -> dist/ArcDesk/{ArcDesk, ArcDeskVoice, _internal}

and the packaged binary starts and runs:

    $ ArcDesk --doctor
    [ok]   Silent spawns   child processes: 23 of 23 spawn sites route through
                           quiet.py (compiled build)
    RESULT: usable, with 1 warning(s)      <- the warning is this sandbox's 0.5 GB
                                              free disk, not the app

Before this pack, the same command produced a NameError in 2 seconds (run #14)
and a packaging shadowing error in 6 seconds (run #15).

    python tests/run_all.py   ->  72/72 passed in 92.6 s

HOW TO APPLY (GitHub Desktop, 3 steps)
--------------------------------------
1. Unzip this pack over the repo folder (paths match exactly).
2. Commit: "spec: load preflight by file path (no sys.path) + shadowing check"
3. Push origin. ~4 minutes.

Then on your PC:
4. Settings > Apps > Arc Desk > Uninstall  (answer NO to deleting the vault)
5. Actions > newest green run > Artifacts > ArcDesk > download BOTH files
6. Fastest working check, no install, no Python:
   unzip ArcDesk-portable.zip > open the folder > double-click ArcDesk.exe
   Inside that folder you should now see ArcDeskVoice.exe too, and the icon is
   Arc Desk's own, not the yellow-and-blue Python box.

IF THE RUN IS RED AGAIN
-----------------------
Send me: the name of the red step, and the ~30 lines above the error. The run
page logs need you to be signed in, so I cannot read them from here - I can only
read step names and durations. A red build is the pipeline working; it is
stopping a broken exe from reaching your desktop.

FILES IN THIS PACK
------------------
  packaging/arcdesk.spec                 loads the helper by file path
  run.py                                 --doctor loads doctor.py by file path
  tools/preflight_win.py                 NEW: shadowing check
  arcdesk/quiet.py                       frozen-aware spawn report
  tools/doctor.py                        uses it
  .github/workflows/build-windows.yml    step 5 waits for exit + RESULT line
  tests/test_spec_exec.py                sections 6b / 6c
  tests/test_windows_build.py            asserts the file-path load
  CAPABILITIES.md                        the post-mortem, in the record
  README-FIX21.txt                       this file
