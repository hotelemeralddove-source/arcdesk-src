@echo off
REM Arc Desk - "speak in MY voice" + "only MY voice wakes it".
REM Everything here is free and download-once. Nothing is installed silently:
REM every step prints what it is about to fetch, how big it is, and why.
setlocal
cd /d "%~dp0"

if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python.exe) else (set PY=python)

echo ============================================================
echo  Arc Desk - voice cloning and voice lock
echo ============================================================
echo.
echo  Scope: TAMIL, HINDI, ENGLISH. Those three are the promise and the tests.
echo  The other Indic languages usually work, but are not claimed.
echo.
echo  What this installs, and how big:
echo    sherpa-onnx + 30 MB speaker model   voice lock (only your voice)
echo    piper + ta/hi/en voices             free fallback voice, fast, no GPU
echo    IndicF5 (optional, ~1.5 GB)         clone your voice in TAMIL + HINDI
echo    XTTS-v2 (optional, ~1.9 GB)         clone your voice in ENGLISH
echo.
echo  Voice cloning needs a GPU to feel instant. On a CPU it works, but slowly -
echo  the app will say so rather than hide it.
echo.
pause

echo.
echo [1/3] voice lock engine (small) ...
%PY% -m pip install --quiet sherpa-onnx || goto :fail
%PY% tools\voice_setup.py lock-model || echo   (model download failed - you can retry later)

echo.
echo [2/3] piper, the free fallback voice (Tamil, Hindi, English) ...
%PY% -m pip install --quiet piper-tts || echo   (piper failed; SAPI will be used instead)
%PY% -c "import piper; print('  piper ok')" >nul 2>&1 || echo   (install the ta/hi/en voices from the app: Settings -^> Voice)

echo.
echo [3/3] cloning engines - this is the big download, answer y or n when asked
choice /c yn /m "Install IndicF5 for Tamil and Hindi cloning (~1.5 GB, GPU recommended)"
if errorlevel 2 goto :skip_indic
%PY% -m pip install --quiet torch transformers soundfile || goto :skip_indic
%PY% -c "from transformers import AutoModel; AutoModel.from_pretrained('ai4bharat/IndicF5', trust_remote_code=True)" || echo   (IndicF5 download failed - retry with internet)
:skip_indic

choice /c yn /m "Install XTTS-v2 for English cloning (~1.9 GB)"
if errorlevel 2 goto :skip_xtts
%PY% -m pip install --quiet coqui-tts || goto :skip_xtts
%PY% -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')" || echo   (XTTS download failed - retry with internet)
:skip_xtts

echo.
echo ============================================================
echo  Now teach it YOUR voice (one clip, 10-12 s of just you talking):
echo.
echo    %PY% tools\voice_setup.py import "C:\path\to\your-clip.mp4"
echo    %PY% tools\voice_setup.py try "vanakkam macha, ellam ready"
echo.
echo  Clean a noisy clip first if you have one (measures SNR before and after):
echo    %PY% tools\clean_voice.py "C:\path\to\clip.mp3" --import --transcript "the words"
echo.
echo  Then lock it to your voice on THIS machine (3 short recordings):
echo.
echo    %PY% tools\voice_setup.py lock-enroll me rec1.wav rec2.wav rec3.wav
echo    %PY% tools\voice_setup.py lock-test rec4.wav
echo    %PY% tools\voice_setup.py lock-on
echo.
echo  A different laptop keeps its own enrolled voice - nothing is shared unless
echo  you copy %APPDATA%\ArcDesk\voiceid yourself.
echo ============================================================
pause
exit /b 0

:fail
echo.
echo [Arc Desk] setup stopped. Python 3.10+ and internet are needed.
echo             Nothing was left half-installed; run this file again any time.
pause
exit /b 1
