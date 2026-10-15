# Local, user-initiated updater. It never performs GitHub Actions, CI or a deployment.
# No unattended or silent installation; Windows will present a UAC confirmation.
[CmdletBinding()]
param(
    [switch]$DownloadAndInstall,
    [ValidateSet('Default','Stable','Beta')][string]$Channel = 'Default'
)
$ErrorActionPreference = 'Stop'
$repo = 'Terridol/plex-cast-explorer'
$releasePage = "https://github.com/$repo/releases"
$optionsPath = Join-Path $env:ProgramData 'PlexCastExplorer\installer-options.ini'
if ($Channel -eq 'Default') {
    $selectedBeta = $false
    if (Test-Path -LiteralPath $optionsPath) {
        $content = Get-Content -LiteralPath $optionsPath -Raw
        $selectedBeta = ($content -match '(?m)^BetaUpdates=1\s*$')
    }
    $Channel = if ($selectedBeta) { 'Beta' } else { 'Stable' }
}
$installed = '0.4.7-beta'
$localExe = Join-Path $PSScriptRoot 'PlexCastExplorer.exe'
if (!(Test-Path $localExe)) { throw "Missing application executable: $localExe" }

function Parse-Version([string]$value) {
    if ($value -notmatch '^v?(\d+)\.(\d+)\.(\d+)(?:[-.]?(alpha|beta|rc)[.-]?(\d+)?)?$') { return $null }
    return [pscustomobject]@{
        Major=[int]$Matches[1]; Minor=[int]$Matches[2]; Patch=[int]$Matches[3]
        Stage=if ($Matches[4]) { $Matches[4].ToLower() } else { '' }
        StageNumber=if ($Matches[5]) { [int]$Matches[5] } else { 0 }
    }
}
function Compare-Version($a,$b) {
    foreach ($field in @('Major','Minor','Patch')) {
        if ($a.$field -ne $b.$field) { return [Math]::Sign($a.$field - $b.$field) }
    }
    $weight = @{alpha=0; beta=1; rc=2; ''=3}
    if ($weight[$a.Stage] -ne $weight[$b.Stage]) { return [Math]::Sign($weight[$a.Stage]-$weight[$b.Stage]) }
    return [Math]::Sign($a.StageNumber - $b.StageNumber)
}

Write-Host "Plex Cast Explorer $installed | Update channel: $Channel"
Write-Host 'Checking published releases (not development branch commits)...'
$headers = @{ 'User-Agent'='PlexCastExplorer-UpdateCheck/0.4.7'; 'Accept'='application/vnd.github+json' }
try {
    $items = @(Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases?per_page=30" -Headers $headers -TimeoutSec 15)
} catch {
    Write-Warning 'Could not check for updates. The running application is unaffected.'
    Write-Host "You can manually check: $releasePage"
    exit 2
}
$local = Parse-Version $installed
$release = $null
$best = $local
foreach ($item in $items) {
    if ($item.draft) { continue }
    if ($item.prerelease -and $Channel -ne 'Beta') { continue }
    $version = Parse-Version ([string]$item.tag_name)
    if (!$version) { continue }
    if ((Compare-Version $version $best) -gt 0) {
        $best = $version
        $release = $item
    }
}
if (!$release) {
    Write-Host 'No newer installer is currently published on your selected channel.'
    Write-Host "Releases: $releasePage"
    exit 0
}
Write-Host "Update available: $($release.tag_name)"
Write-Host "Release notes: $($release.html_url)"
if (!$DownloadAndInstall) {
    Write-Host 'To download and run its installer interactively, use:'
    Write-Host '  powershell -NoProfile -ExecutionPolicy Bypass -File .\check_updates.ps1 -DownloadAndInstall'
    exit 0
}
$asset = @($release.assets) | Where-Object { $_.name -match '^PlexCastExplorer-Setup-v?\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*)?-win-x64\.exe$' } | Select-Object -First 1
if (!$asset) { throw "No Windows installer attached to $($release.tag_name). Open $($release.html_url)" }
# Release-asset digest comes from GitHub's asset metadata. If absent, require
# a manual download; never silently execute a package without verification.
if ([string]$asset.digest -notmatch '^sha256:([0-9a-fA-F]{64})$') {
    throw "Release asset has no GitHub-published SHA-256 digest. Download manually from $($release.html_url)"
}
$expectedHash = $Matches[1].ToLowerInvariant()
$location = Join-Path $env:TEMP 'PlexCastExplorerUpdates'
New-Item -ItemType Directory -Path $location -Force | Out-Null
$installer = Join-Path $location $asset.name
Write-Host "Downloading $($asset.name)..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $installer -UseBasicParsing -TimeoutSec 120
$actualHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($expectedHash -ne $actualHash) {
    Remove-Item -LiteralPath $installer -Force
    throw 'Downloaded installer failed checksum verification. Nothing was installed.'
}
Write-Host 'Checksum verified against GitHub release metadata. Opening the installer...'
Write-Warning 'Verify the publisher and installer options before proceeding. This is not Authenticode validation.'
$answer = Read-Host 'Run the Windows installer now? Type YES'
if ($answer -cne 'YES') { Write-Host "Installer saved at $installer"; exit 0 }
Start-Process -FilePath $installer -Verb RunAs -Wait
