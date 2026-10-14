@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo.
echo =============================================================
echo       Plex Cast Explorer v0.4.5-beta - Windows EXE Builder
echo =============================================================
echo.
echo This builds PlexCastExplorer.exe ON THIS PC using Python.
echo Nothing is executed on GitHub.
echo.

where py.exe >nul 2>nul
if errorlevel 1 goto :missing_python

py -3 -c "import sys; print('Using Python ' + sys.version.split()[0] + ' at ' + sys.executable); sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto :missing_python

py -3 -m pip --version
if errorlevel 1 (
    echo pip was not found. Attempting to enable pip...
    py -3 -m ensurepip --upgrade
    if errorlevel 1 goto :pip_error
)

echo.
echo [1/2] Installing or verifying PyInstaller...
py -3 -m pip install --upgrade "pyinstaller>=6.10,<7"
if errorlevel 1 goto :pip_error

echo.
echo [2/2] Building the complete standalone Windows application...
py -3 -m PyInstaller --noconfirm --clean --onedir --console --name PlexCastExplorer --add-data "static;static" --distpath "%CD%\dist" --workpath "%CD%\build" --specpath "%CD%" "%CD%\app.py"
if errorlevel 1 goto :build_error

if not exist "%CD%\dist\PlexCastExplorer\PlexCastExplorer.exe" goto :build_error

echo.
echo =============================================================
echo BUILD SUCCEEDED.
echo EXE: %CD%\dist\PlexCastExplorer\PlexCastExplorer.exe
echo.
echo NEXT: stop the old Cast Explorer, back up its directory,
echo then right-click INSTALL-SERVICE.cmd and Run as administrator.
echo Do not run both old and new servers at the same time.
echo =============================================================
if not "%CAST_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 0

:missing_python
echo.
echo ERROR: Python 3.10 or newer is not accessible via the py launcher.
echo Verify it by running: py -3 --version
goto :failed

:pip_error
echo.
echo ERROR: Python pip / PyInstaller installation failed.
echo Check the lines above for the package installation error.
goto :failed

:build_error
echo.
echo ERROR: PyInstaller did not build the expected EXE.
echo Copy the error output above so it can be diagnosed.
goto :failed

:failed
echo.
echo The existing Plex Cast Explorer installation has NOT been modified.
if not "%CAST_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 1
