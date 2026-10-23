FIX PACK — for the red Windows build
====================================

HOW TO APPLY (no commands):

1. Extract this folder into your project folder, the one that already has
   run.py inside it  (for you: D:\arcdesk-src\arcdesk-src).
   Windows will ask "replace files?" -> YES.

2. Open GitHub Desktop. It will list the changed files.

3. Bottom-left: write "fix windows ci" in the Summary box -> click
   "Commit to main"  ->  top: "Push origin".

4. GitHub starts the build again by itself.
   Repo -> Actions -> the newest run.

WHAT WAS FIXED (all of it found by your CI run, none reproducible on Linux):

* tests/run_all.py  - decoded test output with the Windows code page, crashed the
                      runner and marked 3 healthy tests as FAIL.
* six test files    - read files with the Windows code page too (test_catalog died on
                      GITHUB.md).
* test_backup       - wrote a 192-second sparse file to prove "disk full". Now instant.
* arcdesk/clone.py  - a plain WAV needed ffmpeg; now Python reads it itself.
* test_holo         - graded speed in absolute ms; now relative to the machine.
* the workflow      - read $LASTEXITCODE from a windowed exe (never set), and now keeps
                      a log when a step fails.

Nothing on your PC is installed or changed by a failed build.
