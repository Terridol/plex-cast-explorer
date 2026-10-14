@echo off
powershell.exe -NoProfile -Command "Unregister-ScheduledTask -TaskName PlexCastExplorer -Confirm:$false -ErrorAction Stop"
echo.
pause
