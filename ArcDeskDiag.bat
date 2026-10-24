@echo off
REM ============================================================================
REM  Arc Desk - DIAGNOSE THIS PC.  Double-click it. Nothing to install.
REM
REM  It answers the questions a screenshot cannot:
REM    * is "python" the Microsoft Store alias? (the AppInstallerPythonRedirector
REM      dialog, and the 0xc0000142 that comes with it)
REM    * is ArcDeskSetup.exe a real download, or a truncated one?
REM    * is the file BLOCKED because it came from the internet? (the commonest
REM      reason a downloaded .exe will not start - and the easiest to fix)
REM    * is the MSVC runtime on this machine? (0xc0000142 again)
REM    * is anything already installed?
REM
REM  It writes ArcDeskDiag.txt next to itself. It changes nothing unless you say
REM  "yes" to unblocking our own files, which is safe and reversible.
REM
REM  No Python is used, and none is needed: this must work on the machine that is
REM  broken precisely BECAUSE Python is the problem.
REM ============================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"
set REPORT=%~dp0ArcDeskDiag.txt
set PYEXE=
set FIXED=0

echo Arc Desk diagnostic - writing %REPORT%
echo (this window stays open until you press a key at the end)
echo.
> "%REPORT%" echo ArcDesk diagnostic
>>"%REPORT%" echo generated %DATE% %TIME%
>>"%REPORT%" echo folder %CD%
>>"%REPORT%" echo.

echo [1/7] this PC ...
>>"%REPORT%" echo == 1. this PC
>>"%REPORT%" powershell -NoProfile -Command "$o=Get-CimInstance Win32_OperatingSystem; '  '+$o.Caption+' '+$o.Version+' '+$o.OSArchitecture" 2>nul
>>"%REPORT%" powershell -NoProfile -Command "'  PowerShell ' + $PSVersionTable.PSVersion.ToString()" 2>nul
>>"%REPORT%" echo.

echo [2/7] what is on this disk ...
>>"%REPORT%" echo == 2. files here
for %%F in (ArcDeskSetup.exe ArcDesk-portable.zip ArcDeskDiag.bat) do (
  if exist "%%F" (
    >>"%REPORT%" echo   %%F  %%~zF bytes
  ) else (
    >>"%REPORT%" echo   %%F  (not in this folder)
  )
)
for /d %%D in (dist arcdesk packaged "Arc Desk") do (
  if exist "%%D" >>"%REPORT%" echo   folder: %%D
)
>>"%REPORT%" echo   expected: portable zip about 92 MB, setup exe about 53 MB.
>>"%REPORT%" echo   A setup exe far under 40 MB is a half download - delete it and
>>"%REPORT%" echo   download again. A zip that will not open is the same thing.
>>"%REPORT%" echo.

echo [3/7] is the download blocked by Windows? ...
>>"%REPORT%" echo == 3. blocked files (Mark of the Web)
set BLOCKED=
for %%F in (ArcDeskSetup.exe ArcDesk-portable.zip) do (
  if exist "%%F" (
    set MARK=
    for /f "delims=" %%S in ('powershell -NoProfile -Command "try{(Get-Item -LiteralPath '%%F' -Stream Zone.Identifier -ErrorAction Stop).Stream}catch{''}" 2^>nul') do set MARK=%%S
    if defined MARK (
      set BLOCKED=!BLOCKED! %%F
      >>"%REPORT%" echo   %%F is BLOCKED - Windows tagged it as "came from the internet"
    )
  )
)
if "!BLOCKED!"=="" (
  >>"%REPORT%" echo   nothing is blocked - good
) else (
  echo.
  echo   Windows is blocking:!BLOCKED!
  echo   Unblocking only removes the "came from the internet" tag. It is safe.
  choice /c YN /n /m "   Unblock these files now? [Y/N] "
  if errorlevel 2 (
    >>"%REPORT%" echo   left blocked - the .exe will keep refusing to start
  ) else (
    for %%F in (ArcDeskSetup.exe ArcDesk-portable.zip) do (
      if exist "%%F" (
        powershell -NoProfile -Command "Unblock-File -LiteralPath '%%F'" >nul 2>&1
        >>"%REPORT%" echo   unblocked %%F
        set FIXED=1
      )
    )
    echo   done.
  )
)
>>"%REPORT%" echo.

echo [4/7] python: is it the Microsoft Store alias? ...
>>"%REPORT%" echo == 4. python
>>"%REPORT%" where python 2>nul
>>"%REPORT%" where python3 2>nul
for /f "delims=" %%P in ('where python 2^>nul') do (
  echo %%P | find /i "WindowsApps" >nul
  if not errorlevel 1 (
    >>"%REPORT%" echo   WARNING: %%P is the Microsoft Store ALIAS
    >>"%REPORT%" echo   That is the AppInstallerPythonRedirector.exe dialog, and it is
    >>"%REPORT%" echo   why an exe built on this PC dies with 0xc0000142.
  )
)
for /f "delims=" %%P in ('where py 2^>nul') do (
  >>"%REPORT%" echo   py launcher: %%P
  if not defined PYEXE set PYEXE=py -3
)
if not defined PYEXE for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYEXE set PYEXE=%%P
if defined PYEXE (
  >>"%REPORT%" echo   using: !PYEXE!
  !PYEXE! -c "import sys,struct;print('  real python:',sys.executable);print('  version:',sys.version.split()[0]);print('  bits:',struct.calcsize('P')*8);print('  base:',sys.base_prefix)" 1>>"%REPORT%" 2>nul
) else (
  >>"%REPORT%" echo   no python on PATH at all
  >>"%REPORT%" echo   (that is fine for RUNNING Arc Desk - the app carries its own)
  >>"%REPORT%" echo   (it only matters for BUILDING it)
)
>>"%REPORT%" echo.

echo [5/7] the MSVC runtime (0xc0000142 lives here) ...
>>"%REPORT%" echo == 5. MSVC runtime
for %%D in (vcruntime140.dll vcruntime140_1.dll msvcp140.dll concrt140.dll) do (
  if exist "%SystemRoot%\System32\%%D" (
    >>"%REPORT%" echo   System32\%%D  present
  ) else (
    >>"%REPORT%" echo   System32\%%D  MISSING
  )
)
if exist "dist\ArcDesk" (
  >>"%REPORT%" echo   shipped next to the built app:
  dir /b "dist\ArcDesk\vc*.dll" 2>nul >>"%REPORT%"
  dir /b "dist\ArcDesk\msvc*.dll" 2>nul >>"%REPORT%"
)
>>"%REPORT%" echo.

echo [6/7] what is installed already ...
>>"%REPORT%" echo == 6. installed copies
if exist "%LOCALAPPDATA%\Programs\ArcDesk\ArcDesk.exe" (
  >>"%REPORT%" echo   installed at %LOCALAPPDATA%\Programs\ArcDesk
) else (
  >>"%REPORT%" echo   not installed in %LOCALAPPDATA%\Programs\ArcDesk
)
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "Arc Desk" 2>nul | find /i "DisplayName" >>"%REPORT%"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v ArcDesk 2>nul | find /i "ArcDesk" >>"%REPORT%"
tasklist /fi "imagename eq ArcDesk.exe" 2>nul | find /i "ArcDesk" >>"%REPORT%"
>>"%REPORT%" echo.

echo [7/7] app execution aliases ...
>>"%REPORT%" echo == 7. App execution alias state (python)
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
  for %%A in ("%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe") do (
    >>"%REPORT%" echo   python.exe alias present, %%~zA bytes
    if %%~zA LSS 2000 (
      >>"%REPORT%" echo   (a stub this small means the Store Python itself is gone)
    )
  )
) else (
  >>"%REPORT%" echo   no python.exe alias
)
>>"%REPORT%" echo.

>>"%REPORT%" echo == what to do with this
>>"%REPORT%" echo 1. If section 3 said BLOCKED and you answered N, run this again and say Y.
>>"%REPORT%" echo 2. If section 4 shows WindowsApps, turn the alias off:
>>"%REPORT%" echo    Settings ^> Apps ^> Advanced app settings ^> App execution aliases
>>"%REPORT%" echo    ^> python.exe and python3.exe OFF. Then install Python from python.org.
>>"%REPORT%" echo 3. To use Arc Desk TODAY without any installer:
>>"%REPORT%" echo    right-click ArcDesk-portable.zip ^> Extract All ^> open the folder
>>"%REPORT%" echo    ^> double-click ArcDesk.exe
>>"%REPORT%" echo 4. Send me ArcDeskDiag.txt (it contains no keys, no personal files).

echo.
echo ------------------------------------------------------------------
echo  Report written: %REPORT%
echo  Send me that file and I will tell you exactly which line is the fault.
if "!FIXED!"=="1" echo  (some files were unblocked - try ArcDeskSetup.exe again)
echo ------------------------------------------------------------------
echo.
pause
endlocal
