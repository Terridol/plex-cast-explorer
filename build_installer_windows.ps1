# Builds a self-contained Inno Setup installer on Windows, without GitHub CI.
# -Release is reserved for approved stable versions built on main.
[CmdletBinding()]
param([switch]$Release)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:OS -ne 'Windows_NT') { throw 'This installer must be compiled on Windows.' }
Set-Location $root

$py = Get-Command 'py.exe' -ErrorAction SilentlyContinue
if (-not $py) { throw 'Python 3.10+ with the py launcher is required for the initial build.' }

# Every release build is fail-closed. No packaging on failed regressions.
$gate = Join-Path $root 'build_gate.py'
if (-not (Test-Path -LiteralPath $gate -PathType Leaf)) { throw 'Required build_gate.py is missing. Build blocked.' }
function Invoke-LocalGate([string]$Stage, [string]$BuildId = '') {
    Write-Host "[BUILD GATE] Running mandatory $Stage validation..."
    $oldPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 can elevate redirected Python stderr to a
        # terminating error even when the child is doing normal diagnostics.
        $ErrorActionPreference = 'Continue'
        if ($BuildId) { & $py.Source -3 $gate $Stage --build-id $BuildId }
        else { & $py.Source -3 $gate $Stage }
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldPreference
    }
    if ($exitCode -ne 0) { throw "Build blocked: $Stage gate failed (exit $exitCode). No release may be published." }
}

Invoke-LocalGate 'source'

# Fail early, before downloading dependencies or compiling a large EXE.
# Derive the application version from source; never require hand-editing
# installer output naming each time the beta version is incremented.
$appSource = Get-Content -LiteralPath (Join-Path $root 'app.py') -Raw -Encoding UTF8
$appVersionMatch = [regex]::Match($appSource, "(?m)^VERSION\s*=\s*'(?<version>[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?)'")
if (-not $appVersionMatch.Success) { throw 'Could not determine safe application version from app.py.' }
$appVersion = $appVersionMatch.Groups['version'].Value
if ($Release) {
    if ($appVersion -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') {
        throw 'Stable Setup requires a final MAJOR.MINOR.PATCH version (no beta/rc suffix).'
    }
    $git = Get-Command 'git.exe' -ErrorAction SilentlyContinue
    if (-not $git) { throw 'Stable Setup requires git.exe to verify the approved release branch.' }
    $branchName = (& $git.Source -C $root branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $branchName -ne 'main') { throw 'Stable Setup must be built from approved main, not dev.' }
    $status = @(& $git.Source -C $root status --porcelain --untracked-files=normal)
    if ($LASTEXITCODE -ne 0 -or $status.Count -gt 0) { throw 'Stable Setup requires a clean checkout, including no untracked files.' }
}

# Compile the standalone application directly: one supported build orchestrator,
# one source gate, and one executable gate. No nested batch scripts.
function Invoke-Python([string[]]$Arguments, [string]$Description) {
    Write-Host "[BUILD] $Description"
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $py.Source -3 @Arguments
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldPreference
    }
    if ($exitCode -ne 0) { throw "$Description failed (exit code $exitCode)." }
}
Invoke-Python @('-c','import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)') 'Python 3.10+ verification'
$pythonPip = @('-m', 'pip', '--version')
$oldPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & $py.Source -3 @pythonPip *> $null
    $pipExitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $oldPreference
}
if ($pipExitCode -ne 0) {
    Invoke-Python @('-m','ensurepip','--upgrade') 'Enable pip'
}
Invoke-Python @('-m','pip','install','--upgrade','pyinstaller>=6.10,<7') 'Install or verify PyInstaller'
$pyInstallerArgs = @(
    '-m','PyInstaller','--noconfirm','--clean','--onedir','--console',
    '--name','PlexCastExplorer','--add-data','static;static',
    '--distpath',(Join-Path $root 'dist'),
    '--workpath',(Join-Path $root 'build'),
    '--specpath',$root,(Join-Path $root 'app.py')
)
Invoke-Python $pyInstallerArgs 'Compile standalone application'
$exe = Join-Path $root 'dist\PlexCastExplorer\PlexCastExplorer.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Missing built application at $exe"
}
Invoke-LocalGate 'exe'

$winswDir = Join-Path $root 'installer-assets'
$winsw = Join-Path $winswDir 'WinSW-x64.exe'
New-Item -ItemType Directory -Force -Path $winswDir | Out-Null
$expected = '05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da'
$installedWinSW = Join-Path $env:ProgramFiles 'PlexCastExplorer\PlexCastExplorerService.exe'
if (-not (Test-Path -LiteralPath $winsw)) {
    if ((Test-Path -LiteralPath $installedWinSW) -and
        ((Get-FileHash -LiteralPath $installedWinSW -Algorithm SHA256).Hash.ToLowerInvariant() -eq $expected)) {
        Copy-Item -LiteralPath $installedWinSW -Destination $winsw
        Write-Host 'Using verified WinSW from the installed application.'
    } else {
        $uri = 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe'
        Write-Host 'Downloading the pinned WinSW service wrapper...'
        Invoke-WebRequest -Uri $uri -OutFile $winsw -UseBasicParsing
    }
}
$actual = (Get-FileHash -LiteralPath $winsw -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) {
    Remove-Item -LiteralPath $winsw -ErrorAction SilentlyContinue
    throw 'WinSW checksum mismatch. Installer build stopped.'
}

function Get-ISCC {
    $command = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($path in @(
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe')
    )) {
        if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) { return $path }
    }
    return $null
}


# Every dev installer receives a unique, filesystem-safe build ID.
# UTC includes milliseconds, so rebuilding the same commit never overwrites
# a previous installer. Prefer the checked-out Git commit, with a local source
# fingerprint fallback for machines without git.exe in PATH.
$utcBuildStamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff')
$fallbackHash = (Get-FileHash -LiteralPath (Join-Path $root 'app.py') -Algorithm SHA256).Hash.Substring(0,8).ToLowerInvariant()
$revision = 's' + $fallbackHash
$gitCommand = Get-Command 'git.exe' -ErrorAction SilentlyContinue
if ($gitCommand) {
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $gitHead = @(& $gitCommand.Source -C $root rev-parse --verify --short=8 HEAD 2>$null)
        $gitExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedPreference
    }
    if ($gitExit -eq 0 -and $gitHead.Count -gt 0 -and $gitHead[-1] -match '^[0-9a-fA-F]{8}$') {
        $revision = 'g' + $gitHead[-1].ToLowerInvariant()
    }
}
$buildId = 'dev-' + $utcBuildStamp + '-' + $revision
if ($buildId -notmatch '^dev-[0-9]{8}-[0-9]{9}-[gs][0-9a-f]{8}$') {
    throw "Invalid development build identifier: $buildId"
}
if ($Release) {
    $buildId = 'release'
    Write-Host "STABLE RELEASE PACKAGE: v$appVersion from approved main"
} else {
    Write-Host "DEV BUILD ID: $buildId"
    Write-Host 'The complete build ID will appear in Setup, Installed Apps and the output filename.'
}

$iscc = Get-ISCC
if (-not $iscc) {
    $winget = Get-Command 'winget.exe' -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'Inno Setup 6 is required. Install it from jrsoftware.org/isinfo.php and retry.' }
    Write-Host 'Installing Inno Setup 6 using winget (a Windows package manager)...'
    $oldPref = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $winget.Source install --id JRSoftware.InnoSetup --exact --accept-source-agreements --accept-package-agreements
        $installExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $oldPref }
    if ($installExit -ne 0) { throw 'Inno Setup install failed or was cancelled. Retry after installing Inno Setup 6.' }
    $iscc = Get-ISCC
    if (-not $iscc) { throw 'Inno Setup installed but ISCC.exe was not found. Reopen PowerShell and retry.' }
}
# Delete an old artifact first: a failed compile must never look like success.
$installer = if ($Release) {
    Join-Path $root ("output\PlexCastExplorer-Setup-$appVersion-win-x64.exe")
} else {
    Join-Path $root ("output\PlexCastExplorer-Setup-$appVersion-$buildId-win-x64.exe")
}
$checksum = $installer + '.sha256'
# Keep older build IDs in the output folder for side-by-side comparison.
# Delete only the current ID's artifact to avoid reporting a stale result.
Remove-Item -LiteralPath $installer,$checksum -Force -ErrorAction SilentlyContinue
Write-Host "Compiling Setup.exe with $iscc"
$oldPref = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    if ($Release) {
        & $iscc '/DReleaseBuild=1' (Join-Path $root 'PlexCastExplorer.iss')
    } else {
        & $iscc ('/DDevBuildId=' + $buildId) (Join-Path $root 'PlexCastExplorer.iss')
    }
    $compilerExit = $LASTEXITCODE
} finally { $ErrorActionPreference = $oldPref }
if ($compilerExit -ne 0) { throw "Inno Setup compiler failed (exit $compilerExit)." }
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Installer compilation reported success but expected output was absent.' }
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath ($installer + '.sha256') -Value ($hash + '  ' + [IO.Path]::GetFileName($installer)) -Encoding ASCII
Write-Host "SUCCESS: $installer"
Write-Host "SHA-256: $hash"
try {
    Invoke-LocalGate 'installer' -BuildId $buildId
} catch {
    Remove-Item -LiteralPath $installer,$checksum -Force -ErrorAction SilentlyContinue
    throw
}
Write-Host 'LOCAL BUILD GATE PASSED: source tests, EXE smoke, compiler and installer artifact checks.'
Write-Host 'Installer not yet smoke-tested; back up your current data before running the upgrade.'
