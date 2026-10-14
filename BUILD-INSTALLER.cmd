@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===============================================================
echo   Plex Cast Explorer - Windows Setup Builder (v0.4.6 beta)
echo ===============================================================
echo.
echo Creates a single Windows Setup EXE with installation options,
echo in-place upgrades, Windows service and a scoped firewall rule.
echo No GitHub Actions or hosted builds will be run.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_installer_windows.ps1"
set "result=%ERRORLEVEL%"
echo.
if "%result%"=="0" (
  echo Setup build successful. See the output folder.
) else (
  echo Installer build FAILED. Read the error above. Existing service unchanged.
)
pause
exit /b %result%
