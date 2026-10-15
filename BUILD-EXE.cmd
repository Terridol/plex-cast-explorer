@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo =============================================================
echo Plex Cast Explorer v0.4.7-beta - Gated Windows EXE Builder
echo =============================================================
echo Runs ALL local regressions and launches the built EXE in isolation.
echo.

where py.exe >nul 2>nul
if errorlevel 1 goto :missing_python
py -3 -c "import sys; print('Python '+sys.version.split()[0]); sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto :missing_python

echo [GATE 1/2] Source regression tests and installer safety contracts...
py -3 build_gate.py source
if errorlevel 1 goto :test_error

py -3 -m pip --version >nul
if errorlevel 1 (
    py -3 -m ensurepip --upgrade
    if errorlevel 1 goto :pip_error
)

echo [BUILD] Installing/verifying PyInstaller...
py -3 -m pip install --upgrade "pyinstaller>=6.10,<7"
if errorlevel 1 goto :pip_error

echo [BUILD] Compiling standalone Windows application...
py -3 -m PyInstaller --noconfirm --clean --onedir --console --name PlexCastExplorer --add-data "static;static" --distpath "%CD%\dist" --workpath "%CD%\build" --specpath "%CD%" "%CD%\app.py"
if errorlevel 1 goto :build_error
if not exist "%CD%\dist\PlexCastExplorer\PlexCastExplorer.exe" goto :build_error

echo [GATE 2/2] Booting compiled EXE with isolated temporary data...
py -3 build_gate.py exe
if errorlevel 1 goto :test_error

echo.
echo EXE BUILD GATE PASSED. Continue with BUILD-INSTALLER.cmd.
if not "%CAST_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 0

:missing_python
echo ERROR: Python 3.10+ launcher unavailable. Build blocked.
goto :failed

:pip_error
echo ERROR: pip/PyInstaller installation failed. Build blocked.
goto :failed

:build_error
echo ERROR: PyInstaller EXE compilation failed. Build blocked.
goto :failed

:test_error
echo ERROR: Regression or compiled EXE smoke test failed. Build blocked.
goto :failed

:failed
echo Your installed Windows service and data were not modified.
if not "%CAST_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 1