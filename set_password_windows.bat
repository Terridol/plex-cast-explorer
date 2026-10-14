@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 manage.py set-password
) else (
    python manage.py set-password
)
echo.
pause
