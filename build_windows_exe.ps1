# Build a Windows executable locally. No GitHub Actions or hosted build is involved.
param([switch]$InstallPyInstaller)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq 'Core' -and $env:OS -ne 'Windows_NT') { throw 'Run this script on Windows.' }
$launcher = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { throw 'Install Python 3.10+ for Windows first.' }
$argsPrefix = if ($launcher -eq 'py') { @('-3') } else { @() }
& $launcher @argsPrefix -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    if (-not $InstallPyInstaller) { throw 'PyInstaller is missing. Re-run with -InstallPyInstaller to install it from PyPI.' }
    & $launcher @argsPrefix -m pip install 'pyinstaller>=6.10,<7'
    if ($LASTEXITCODE -ne 0) { throw 'Unable to install PyInstaller.' }
}
$arguments = @('-m','PyInstaller','--onedir','--noconfirm','--clean','--console','--name','PlexCastExplorer',
    '--add-data',"$root\static;static",'--distpath',"$root\dist",'--workpath',"$root\build",
    '--specpath',$root,"$root\app.py")
& $launcher @argsPrefix @arguments
if ($LASTEXITCODE -ne 0) { throw 'Windows EXE build failed.' }
$exe = Join-Path $root 'dist\PlexCastExplorer\PlexCastExplorer.exe'
if (-not (Test-Path $exe)) { throw 'PyInstaller did not create the expected executable.' }
Write-Host "Built executable locally: $exe"
Write-Host 'Next: install_service_windows.ps1 (run elevated after backing up your existing installation).'
