# Builds a self-contained Inno Setup installer on Windows, without GitHub CI.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:OS -ne 'Windows_NT') { throw 'This installer must be compiled on Windows.' }
Set-Location $root

$py = Get-Command 'py.exe' -ErrorAction SilentlyContinue
if (-not $py) { throw 'Python 3.10+ with the py launcher is required for the initial build.' }
$env:CAST_BUILD_NONINTERACTIVE='1'
try {
    & cmd.exe /d /c ('"' + (Join-Path $root 'BUILD-EXE.cmd') + '"')
    $status = $LASTEXITCODE
} finally {
    Remove-Item Env:CAST_BUILD_NONINTERACTIVE -ErrorAction SilentlyContinue
}
if ($status -ne 0) { throw "Windows EXE build failed (exit $status)." }
$exe = Join-Path $root 'dist\PlexCastExplorer\PlexCastExplorer.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Missing built application at $exe" }

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

Write-Host "Compiling Setup.exe with $iscc"
$oldPref = $ErrorActionPreference
try {
    $ErrorActionPreference = 'Continue'
    & $iscc (Join-Path $root 'PlexCastExplorer.iss')
    $compilerExit = $LASTEXITCODE
} finally { $ErrorActionPreference = $oldPref }
if ($compilerExit -ne 0) { throw "Inno Setup compiler failed (exit $compilerExit)." }
$installer = Join-Path $root 'output\PlexCastExplorer-Setup-0.4.7-beta-win-x64.exe'
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Installer compilation reported success but expected output was absent.' }
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath ($installer + '.sha256') -Value ($hash + '  ' + [IO.Path]::GetFileName($installer)) -Encoding ASCII
Write-Host "SUCCESS: $installer"
Write-Host "SHA-256: $hash"
Write-Host 'Installer not yet smoke-tested; back up your current data before running the upgrade.'
