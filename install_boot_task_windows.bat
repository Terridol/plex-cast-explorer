@echo off
cd /d "%~dp0"
echo Open PowerShell as Administrator in this folder and run:
echo     powershell -NoProfile -ExecutionPolicy Bypass -File ".\install_boot_task_windows.ps1"
echo.
echo Boot mode requires all-users Python and does not need an interactive login.
pause
