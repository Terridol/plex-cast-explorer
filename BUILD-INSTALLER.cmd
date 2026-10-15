@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ===============================================================
echo   Plex Cast Explorer - Windows Setup Builder (v1.0.0 release candidate)
echo ===============================================================
echo.
echo Creates a single Windows Setup EXE with installation options,
echo in-place upgrades, Windows service and a scoped firewall rule.
echo No GitHub Actions or hosted builds will be run.
echo.
echo [PRE-FLIGHT] Validating all PowerShell scripts before starting build...
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0scripts\validate_powershell.ps1"
if errorlevel 1 (
  echo.
  echo BUILD BLOCKED: PowerShell syntax check failed. Installer was not built.
  pause
  exit /b 1
)
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
