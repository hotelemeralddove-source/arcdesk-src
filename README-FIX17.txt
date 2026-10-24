ARC DESK — FIX PACK 17
"ArcDeskSetup.exe will not start (0xc0000142)"
================================================================

WHAT YOU SAW
------------
    AppInstallerPythonRedirector.exe - Application Error
    The application was unable to start correctly (0xc0000142).

WHAT IT ACTUALLY MEANS
----------------------
AppInstallerPythonRedirector.exe is NOT part of Arc Desk. It is the
Microsoft Store's Python alias - the stub Windows runs when something
asks for "python.exe" and the only Python is the Store package. Its name
in the title is proof that Python was launched, and that Python is the
Store alias.

0xc0000142 = STATUS_DLL_INIT_FAILED. Two ways to get it:

  1. THE EXE WAS BUILT WITH THE STORE PYTHON.
     PyInstaller copies DLLs out of the Store package folder, which has
     restricted permissions, so the frozen app cannot initialise them.
     The build says OK, the exe never opens.

  2. THE PC HAS NO MSVC RUNTIME.
     Qt needs vcruntime140.dll / msvcp140.dll. Windows only has them in
     System32 if something installed the VC++ Redistributable first.

  3. (also: the download is truncated or blocked - check the size. Your
     setup exe is 53,869 KB, which is the right size, so this is less
     likely, but ArcDeskDiag.bat checks it anyway.)

USE IT TODAY — no installer, no Python, nothing to fix first
------------------------------------------------------------
1. Right-click ArcDesk-portable.zip
2. Extract All
3. Open the extracted folder
4. Double-click ArcDesk.exe

Nothing is registered, nothing is installed. Delete the folder when you
are done and you have uninstalled it.

WHAT IS FIXED IN THE CODE (so it cannot happen again)
-----------------------------------------------------
* tools/preflight_win.py  - NEW. Step 0 of build.bat and build_all.bat.
  Judged BEFORE PyInstaller runs: Store alias (by path AND base_prefix),
  32-bit, Python < 3.9, no venv, missing PySide6/PyInstaller, missing
  Inno Setup, low disk, OneDrive folder, path > 110 chars.
  Exit 1, with the one action that fixes it. A build that cannot open
  can no longer be produced silently.

* packaging/arcdesk.spec - the MSVC runtime DLLs are now collected from
  the build interpreter and shipped NEXT TO the exe. That is the actual
  cure for 0xc0000142 on a clean PC.

* packaging/pyi_rth_arcdesk.py - NEW. A PyInstaller runtime hook that
  points stdout/stderr at %APPDATA%\ArcDesk\logs\arcdesk.log and starts
  the log BEFORE run.py is imported. A windowed build that dies in its
  first second now leaves a traceback instead of absolutely nothing.

* ArcDeskDiag.bat - NEW. Double-click it: no Python, no install.
  It reports the OS, the file sizes, whether the download is BLOCKED
  (Mark of the Web - read from the real Zone.Identifier stream),
  whether python is the Store alias, whether the MSVC runtime exists,
  what is already installed, and the App Execution Alias state.
  It offers to unblock our files (nothing else is touched), writes
  ArcDeskDiag.txt, and tells you the four things to do with it.

* TROUBLESHOOT.md - NEW. Every dialog with its cause and its clicks,
  starting with the no-installer route.

* requirements-build.txt - NEW. PyInstaller declared as a BUILD tool,
  not a runtime dependency (tests/test_audit.py refuses undeclared
  imports, and it is right to).

VERIFIED
--------
  python tests/run_all.py        ->  71/71 passed in 84.3 s
  python tests/test_windows_build.py (new, 10 sections):
      * the Store alias is refused by path, by base_prefix, by name
      * 32-bit and Python 3.8 are refused; 3.9 warns; 3.11 in a venv passes
      * every refusal carries the exact fix
      * the MSVC collector finds DLLs, ships them flat, invents nothing
      * the spec wires both the runtime and the runtime hook
      * build.bat and build_all.bat run the preflight BEFORE PyInstaller
        (the test looks for "-m PyInstaller", not the word in a comment)
      * the diagnostic reads the real Zone.Identifier stream, asks before
        changing anything, never deletes a download
      * the guide offers the no-installer route first
  python tools/preflight_win.py   -> runs, prints the table, exit 0/1
  smoke_firstrun (offscreen)      -> ALL PASS, no traceback, clean exit

WHAT I STILL CANNOT SEE FROM HERE
---------------------------------
This sandbox is Linux. I cannot double-click a Windows installer, so I
have NOT seen your dialog disappear. What is proven: the rules that
produce that class of broken build, the source scan that stops them, and
the diagnostic that reads your machine.

WHAT I NEED FROM YOU (30 seconds)
---------------------------------
  1. Run: right-click ArcDesk-portable.zip -> Extract All -> open folder
     -> double-click ArcDesk.exe
  2. Tell me: did the window open?
       YES -> the app is fine, only the installer was broken. I rebuild it
              with a real Python.
       NO  -> double-click ArcDeskDiag.bat in the same folder and send me
              ArcDeskDiag.txt. That file tells me which of the three
              causes it is, in one page.

FILES IN THIS PACK
------------------
  tools/preflight_win.py            NEW
  packaging/pyi_rth_arcdesk.py      NEW
  ArcDeskDiag.bat                   NEW
  TROUBLESHOOT.md                   NEW
  requirements-build.txt            NEW
  tests/test_windows_build.py       NEW
  packaging/arcdesk.spec            MSVC runtime + runtime hook
  packaging/build.bat               preflight as step 0
  packaging/build_all.bat           preflight as step 0
  tests/test_audit.py               build deps declared
  tests/test_docs.py                ArcDeskDiag.txt is generated, not shipped
  COMMANDS.md CAPABILITIES.md README.md MACHI.md REEVAL.md CROSSCHECK.md
  SETUP_GITHUB.md WHATS_INCLUDED.md test counts 70 -> 71
  README-FIX17.txt                  this file
