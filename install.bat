@echo off
REM Arc Desk - one-time setup. Creates a local venv so nothing global is touched.
setlocal
cd /d "%~dp0"

where py >nul 2>nul && (set PY=py -3) || (set PY=python)

echo [Arc Desk] creating virtual environment .venv ...
%PY% -m venv .venv || goto :fail
call .venv\Scripts\activate.bat

echo [Arc Desk] installing dependencies ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt || goto :fail

echo.
echo [Arc Desk] done. Launch with:  start_arcdesk.vbs   (no console window)
echo            or:                  .venv\Scripts\python run.py
pause
exit /b 0

:fail
echo.
echo [Arc Desk] setup failed. Is Python 3.10+ installed and on PATH?
pause
exit /b 1
