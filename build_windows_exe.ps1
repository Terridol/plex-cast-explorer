# Build Plex Cast Explorer locally on Windows. No GitHub Actions or remote build.
param([switch]$InstallPyInstaller)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:OS -ne 'Windows_NT') { throw 'Run this build script on Windows.' }

# Resolve an actual Python interpreter. Do not accept the Windows Store
# App Execution Alias at %LOCALAPPDATA%\Microsoft\WindowsApps\python.exe.
$python = $null
$launcher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
if ($launcher) {
    $previous = $ErrorActionPreference
    try {
        # Native stderr becomes NativeCommandError with Stop in Windows PowerShell
        # 5.1. Do not use that setting for native executable probes.
        $ErrorActionPreference = 'Continue'
        $found = & $launcher.Source -3 -c 'import sys; print(sys.executable)' 2>$null
        $status = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($status -eq 0 -and $found) {
        $candidate = @($found)[-1].ToString().Trim()
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $python = $candidate
        }
    }
}

if (-not $python) {
    $command = Get-Command 'python.exe' -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notmatch '(?i)\\WindowsApps\\') {
        $python = $command.Source
    }
}
if (-not $python) {
    throw 'Python 3.10+ was not found. Install it with winget, reopen PowerShell, and confirm: py -3 -c "import sys; print(sys.executable)"'
}

# Check the interpreter using a predictable, non-interactive command.
$previous = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    $version = & $python -c 'import sys; print("%d.%d.%d" % sys.version_info[:3]); sys.exit(0 if sys.version_info >= (3,10) else 1)'
    $status = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previous
}
if ($status -ne 0) { throw "Python 3.10+ required. Selected: $python" }
Write-Host "Using Python $version at $python"

# Probe by import rather than running 'PyInstaller --version' with stderr
# redirected. That older probe stopped the whole script before pip could run.
$previous = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & $python -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)"
    $hasPyInstaller = ($LASTEXITCODE -eq 0)
} finally {
    $ErrorActionPreference = $previous
}

if (-not $hasPyInstaller) {
    if (-not $InstallPyInstaller) {
        throw 'PyInstaller is missing. Re-run with -InstallPyInstaller.'
    }
    Write-Host 'Installing PyInstaller for the selected Python...'
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $python -m pip install 'pyinstaller>=6.10,<7'
        $status = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($status -ne 0) { throw 'PyInstaller installation failed. Check pip and network connectivity.' }
}

$arguments = @(
    '-m','PyInstaller',
    '--onedir','--noconfirm','--clean','--console',
    '--name','PlexCastExplorer',
    '--add-data',"$root\static;static",
    '--distpath',"$root\dist",
    '--workpath',"$root\build",
    '--specpath',$root,
    "$root\app.py"
)
Write-Host 'Building PlexCastExplorer.exe...'
$previous = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & $python @arguments
    $status = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previous
}
if ($status -ne 0) { throw "PyInstaller build failed (exit code $status)." }

$exe = Join-Path $root 'dist\PlexCastExplorer\PlexCastExplorer.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw 'Build returned success but the expected PlexCastExplorer.exe is missing.'
}
Write-Host "Built Windows executable: $exe"
Write-Host 'Do not run the service installer until the executable has been smoke-tested.'
