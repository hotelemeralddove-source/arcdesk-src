@echo off
REM Arc Desk - optional voice backend. Installs speech engines only, no models.
setlocal
cd /d "%~dp0"

if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=python)

echo [Arc Desk] installing voice backend (vosk + sounddevice) ...
%PY% -m pip install --quiet -r requirements-voice.txt || goto :fail

echo.
echo [Arc Desk] downloading the 40 MB speech model ...
%PY% arc_daemon.py --download-model

echo.
echo [Arc Desk] done. In the app: click "WAKE OFF" in the header, then say "Hey Jarvis".
echo            Test without a mic first:  menu -^> "Test wake word (no mic)"
echo.
echo With these installed, "BYE JARVIS" can also CLOSE the app and keep a launcher
echo listening, so "HEY JARVIS" starts it again. Settings -^> On "BYE JARVIS".
echo Without them the app stays open on "bye jarvis" and tells you why - it never
echo quits and leaves you with nothing to call it back.
pause
exit /b 0

:fail
echo [Arc Desk] voice setup failed. Python 3.10+ and internet needed for the model download.
pause
exit /b 1
