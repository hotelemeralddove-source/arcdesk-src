@echo off
REM Arc Desk - no-installer shortcut setup (works on any Windows build).
REM Creates Start Menu + desktop shortcuts and optionally the startup entry.
setlocal
cd /d "%~dp0"

set "EXE=%~dp0build\dist\ArcDesk\ArcDesk.exe"
if not exist "%EXE%" set "EXE=%~dp0ArcDesk.exe"
if not exist "%EXE%" (
    echo   ArcDesk.exe not found. Build it first:  build\build.bat
    pause
    exit /b 1
)

echo [Arc Desk] creating shortcuts for:
echo   %EXE%
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$exe='%EXE%';" ^
  "$sm=[Environment]::GetFolderPath('Programs');" ^
  "$dt=[Environment]::GetFolderPath('Desktop');" ^
  "$sh=New-Object -ComObject WScript.Shell;" ^
  "$s=$sh.CreateShortcut(\"$sm\Arc Desk.lnk\"); $s.TargetPath=$exe; $s.Arguments='--show'; $s.Save();" ^
  "$d=$sh.CreateShortcut(\"$dt\Arc Desk.lnk\"); $d.TargetPath=$exe; $d.Arguments='--show'; $d.Save();" ^
  "Write-Host '  Start Menu + Desktop shortcuts created.'"

echo.
set /p ANS="Start Arc Desk silently when Windows starts? (y/N) "
if /i "%ANS%"=="y" (
    powershell -NoProfile -Command ^
      "$startup=[Environment]::GetFolderPath('Startup');" ^
      "$sh=New-Object -ComObject WScript.Shell;" ^
      "$s=$sh.CreateShortcut(\"$startup\Arc Desk.lnk\");" ^
      "$s.TargetPath='%EXE%'; $s.Arguments='--shadow'; $s.Save();" ^
      "Write-Host '  Startup entry created (silent, wake word only).'"
)

echo.
echo   Done. Say "Hey JARVIS" once the app has been opened once and the wake word is enabled.
pause
