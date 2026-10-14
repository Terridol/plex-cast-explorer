@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py
) else (
    python app.py
)
if errorlevel 1 (
    echo.
    echo Unable to start. Check Python 3.10+ and whether port 8765 is already in use.
    echo Review server.log for details.
    pause
)
