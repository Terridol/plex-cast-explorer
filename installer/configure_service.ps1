# Executed elevated by Inno Setup after application files have been installed.
# Safe for first installation and subsequent in-place upgrades.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$InstallDir,
    [ValidateRange(1024,65535)][int]$Port = 8765,
    [ValidateSet(0,1)][int]$EnableTMDB = 0,
    [ValidateSet(0,1)][int]$CreateFirewall = 1,
    [ValidateSet(0,1)][int]$AllowBetaUpdates = 0,
    [string]$RemoteAdminCIDRs = ''
)
$ErrorActionPreference = 'Stop'
$serviceName = 'PlexCastExplorer'
$ruleName = 'PlexCastExplorer-Inbound-Private'
$dataDir = Join-Path $env:ProgramData 'PlexCastExplorer'
$exe = Join-Path $InstallDir 'PlexCastExplorer.exe'
$wrapper = Join-Path $InstallDir 'PlexCastExplorerService.exe'
$xmlPath = Join-Path $InstallDir 'PlexCastExplorerService.xml'
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw 'The installer must be run as Administrator.' }
if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Application executable missing: $exe" }
if (!(Test-Path -LiteralPath $wrapper -PathType Leaf)) { throw "Service wrapper missing: $wrapper" }
if ($InstallDir -match '[<>]') { throw 'Install path includes unsupported XML characters.' }

$addresses = @()
if ($RemoteAdminCIDRs.Trim()) {
    foreach ($value in ($RemoteAdminCIDRs -split ',')) {
        $range = $value.Trim()
        if (!$range) { throw 'Remote admin CIDR list contains an empty entry.' }
        $ipPart = ($range -split '/')[0]
        $parsedIP = $null
        if (-not [Net.IPAddress]::TryParse($ipPart, [ref]$parsedIP)) { throw "Invalid VPN CIDR: $range" }
        if ($range -notmatch '/\d+$') { throw "Use VPN addresses with CIDR masks, e.g. 10.10.20.6/32: $range" }
        $bits = [int](($range -split '/')[-1])
        $maxBits = if ($parsedIP.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork) { 32 } else { 128 }
        if ($bits -lt 0 -or $bits -gt $maxBits) { throw "Invalid VPN CIDR mask: $range" }
        if ($parsedIP.IsIPv6Multicast) { throw "Multicast VPN range is not allowed: $range" }
        $addresses += $range
    }
}

# Keep an automatic pre-upgrade snapshot of settings and SQLite files.
# The Windows service is stopped by Inno Setup before installation.
$oldService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($oldService -and (Test-Path -LiteralPath $dataDir -PathType Container)) {
    $backup = Join-Path $dataDir ('backups\pre-upgrade-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    foreach ($file in @('config.json','auth.json','admin_auth.json','artwork_config.json',
                        'network.json','cast_explorer.db','cast_explorer.db-wal','cast_explorer.db-shm')) {
        $source = Join-Path $dataDir $file
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            Copy-Item -LiteralPath $source -Destination $backup -ErrorAction Stop
        }
    }
}

# Leave all existing runtime state intact during upgrades.
New-Item -ItemType Directory -Force -Path $dataDir,(Join-Path $dataDir 'portraits'),(Join-Path $dataDir 'logs') | Out-Null
& icacls.exe $dataDir /inheritance:r | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Unable to restrict the runtime directory ACL.' }
& icacls.exe $dataDir /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)M' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Unable to grant the service account write access to runtime state.' }

[xml]$xml = New-Object xml
$null = $xml.AppendChild($xml.CreateXmlDeclaration('1.0', 'utf-8', $null))
$svc = $xml.CreateElement('service'); $null = $xml.AppendChild($svc)
function Add-SvcNode([string]$name,[string]$value) {
    $node = $xml.CreateElement($name)
    $node.InnerText = $value
    $null = $svc.AppendChild($node)
    return $node
}
$null = Add-SvcNode 'id' $serviceName
$null = Add-SvcNode 'name' 'Plex Cast Explorer'
$null = Add-SvcNode 'description' 'Plex performer gallery for trusted private networks'
$null = Add-SvcNode 'executable' $exe
$null = Add-SvcNode 'workingdirectory' $InstallDir
$null = Add-SvcNode 'startmode' 'Automatic'
$null = Add-SvcNode 'delayedAutoStart' 'true'
$account = $xml.CreateElement('serviceaccount')
$username = $xml.CreateElement('username'); $username.InnerText = 'NT AUTHORITY\LocalService'
$null = $account.AppendChild($username); $null = $svc.AppendChild($account)
foreach ($pair in @(
    @('CAST_EXPLORER_DATA_DIR', $dataDir),
    @('CAST_EXPLORER_PORT', "$Port"),
    @('CAST_EXPLORER_ENABLE_TMDB', $(if ($EnableTMDB -eq 1) { '1' } else { '0' })),
    @('CAST_EXPLORER_REMOTE_ADMIN_CIDRS', ($addresses -join ','))
)) {
    $node = $xml.CreateElement('env')
    $node.SetAttribute('name', $pair[0]); $node.SetAttribute('value', [string]$pair[1])
    $null = $svc.AppendChild($node)
}
$null = Add-SvcNode 'logpath' (Join-Path $dataDir 'logs')
$logNode = $xml.CreateElement('log'); $logNode.SetAttribute('mode','roll'); $null = $svc.AppendChild($logNode)
$failureNode = $xml.CreateElement('onfailure'); $failureNode.SetAttribute('action','restart'); $failureNode.SetAttribute('delay','15 sec'); $null = $svc.AppendChild($failureNode)
$null = Add-SvcNode 'stoptimeout' '25 sec'
$xml.Save($xmlPath)

$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -ne 'Stopped') {
        Stop-Service -Name $serviceName -Force -ErrorAction Stop
        (Get-Service -Name $serviceName).WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    }
    & $wrapper refresh
    if ($LASTEXITCODE -ne 0) { throw 'Could not refresh the installed Windows service. Check the service logs.' }
} else {
    & $wrapper install
    if ($LASTEXITCODE -ne 0) { throw 'Windows service registration failed.' }
}

# Firewall settings are actively managed on upgrades, not duplicated.
Get-NetFirewallRule -DisplayName 'Plex Cast Explorer (private LAN only)' -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction Stop
Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction Stop
if ($CreateFirewall -eq 1) {
    $remote = @('LocalSubnet') + $addresses
    New-NetFirewallRule -Name $ruleName -DisplayName 'Plex Cast Explorer (Private LAN and approved VPN)' `
      -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Program $exe `
      -Profile Private -RemoteAddress $remote -Enabled True -ErrorAction Stop | Out-Null
}

# Save non-secret installer options so future upgrades retain the choices.
$settingsPath = Join-Path $dataDir 'installer-options.ini'
@('[Service]',"Port=$Port","RemoteAdminCIDRs=$($addresses -join ',')",
  "EnableTMDB=$([int]$EnableTMDB)","CreateFirewall=$([int]$CreateFirewall)",
  "BetaUpdates=$([int]$AllowBetaUpdates)") | Set-Content -LiteralPath $settingsPath -Encoding ASCII

& $wrapper start
if ($LASTEXITCODE -ne 0) { throw 'Installed/updated service could not start. Check Event Viewer and ProgramData logs.' }
(Get-Service -Name $serviceName).WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
Write-Host "Plex Cast Explorer service running on port $Port. Runtime files preserved in $dataDir"
if (-not (Test-Path -LiteralPath (Join-Path $dataDir 'auth.json'))) {
    Write-Host 'NEW INSTALL: Set a gallery password using the Start Menu shortcut before allowing gallery access.'
}
if ($addresses.Count -gt 0 -and -not (Test-Path -LiteralPath (Join-Path $dataDir 'admin_auth.json'))) {
    Write-Host 'Remote administrator allowlist set; configure a separate admin password using the Start Menu shortcut.'
}
