@echo off
REM Arc Desk - validate this checkout in one go. Nothing here changes anything.
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=python)

echo.
echo [1/9] does saying "bye jarvis" really close it?  (real app, real protocol) ...
%PY% tools\voice_roundtrip.py --case quit
echo.
echo [2/9] does it actually boot?  (run.py --shadow, 6 s, isolated) ...
%PY% tools\smoke_firstrun.py --shadow --no-instance --seconds 6
echo.
echo [3/9] tests ...
%PY% tests\run_all.py
echo.
echo [4/9] install check ...
%PY% run.py --doctor
echo.
echo [5/9] is Windows still untouched? ...
%PY% tools\desktop_check.py --scan
echo.
echo [6/9] open-source stack on this PC ...
%PY% tools\github_scan.py --plan
echo.
echo [7/9] what can it actually do? ...
%PY% tools\capability.py --all
echo.
echo [8/9] can this be packaged and uninstalled safely? ...
%PY% tools\packaging.py
echo.
echo [9/9] the tools reference matches the code ...
%PY% tools\gen_tools_doc.py --check
echo.
pause
