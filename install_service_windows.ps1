# Install the compiled Cast Explorer application as a Windows boot-start service.
# Must be run from an elevated Windows PowerShell session. No hosted GitHub jobs.
param(
    [string]$ExistingDataDir = 'D:\plex-cast-explorer',
    [string]$InstallDir = "$env:ProgramFiles\PlexCastExplorer",
    [string]$DataDir = "$env:ProgramData\PlexCastExplorer",
    [switch]$EnableTMDB,
    [string]$RemoteAdminCIDRs = '',
    [switch]$AllowPrivateLanFirewall
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exeSource = Join-Path $root 'dist\PlexCastExplorer\PlexCastExplorer.exe'
if (-not (Test-Path $exeSource)) { throw "Missing $exeSource. Run build_windows_exe.ps1 on Windows first." }
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw 'Run PowerShell as Administrator.' }
if ([Environment]::Is64BitOperatingSystem -ne $true) { throw 'This installer requires 64-bit Windows.' }
if ($RemoteAdminCIDRs -and $RemoteAdminCIDRs -notmatch '^([0-9a-fA-F:.]+/[0-9]{1,3})(,\s*[0-9a-fA-F:.]+/[0-9]{1,3})*$') {
    throw 'RemoteAdminCIDRs must be comma-separated numeric IP CIDR ranges (prefer specific VPN device /32 or /128 addresses).'
}
$existingService = Get-Service -Name PlexCastExplorer -ErrorAction SilentlyContinue
if ($existingService) { throw 'An existing PlexCastExplorer service was detected. Stop and uninstall it before performing this migration.' }
$listener = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($listener) { throw 'Port 8765 is already in use. Stop the old manually launched app BEFORE migrating, then retry.' }
$task = Get-ScheduledTask -TaskName PlexCastExplorer -ErrorAction SilentlyContinue
if ($task -and $task.State -ne 'Disabled') { throw 'An automatic startup task is still enabled. Disable that task before installing the Windows service.' }
if (-not (Test-Path $ExistingDataDir)) { throw "Existing data directory $ExistingDataDir not found. Use -ExistingDataDir with your current Cast Explorer folder." }
if (([IO.Path]::GetFullPath($ExistingDataDir).TrimEnd('\')) -eq ([IO.Path]::GetFullPath($DataDir).TrimEnd('\'))) { throw 'ExistingDataDir and DataDir must be different to preserve a migration backup.' }
$confirm = Read-Host "This will migrate Cast Explorer into '$DataDir' and install an auto-start service in '$InstallDir'. Have you backed up the existing directory? Type YES"
if ($confirm -cne 'YES') { throw 'Cancelled. Backup confirmation required.' }
New-Item -ItemType Directory -Force -Path $InstallDir,$DataDir,(Join-Path $DataDir 'logs') | Out-Null
# Do not grant the LocalService account write access to service executables or service XML.
# Restrict runtime state to Administrators, SYSTEM, and the low-privilege service account.
& icacls.exe $DataDir /inheritance:r | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not restrict runtime data permissions.' }
& icacls.exe $DataDir /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-19:(OI)(CI)M' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not grant the LocalService account runtime data access.' }
$allowed = @('config.json','auth.json','admin_auth.json','artwork_config.json','network.json','cast_explorer.db','cast_explorer.db-wal','cast_explorer.db-shm')
foreach ($name in $allowed) {
    $from=Join-Path $ExistingDataDir $name; $to=Join-Path $DataDir $name
    if ((Test-Path $from) -and -not (Test-Path $to)) { Copy-Item -LiteralPath $from -Destination $to -ErrorAction Stop }
}
$portraitFrom=Join-Path $ExistingDataDir 'portraits'
$portraitTo=Join-Path $DataDir 'portraits'
if ((Test-Path $portraitFrom) -and -not (Test-Path $portraitTo)) { Copy-Item -LiteralPath $portraitFrom -Destination $portraitTo -Recurse -ErrorAction Stop }
if (-not (Test-Path (Join-Path $DataDir 'auth.json'))) { throw 'Gallery password has not been configured. Run set_password_windows.bat in the original installation first.' }
Copy-Item -Path (Join-Path $root 'dist\PlexCastExplorer\*') -Destination (Join-Path $InstallDir '.') -Recurse -Force
$binary = Join-Path $InstallDir 'PlexCastExplorer.exe'
if (-not (Test-Path $binary)) { throw 'Executable installation failed.' }
$wrapper = Join-Path $InstallDir 'PlexCastExplorerService.exe'
$url = 'https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe'
$expected = '05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da'
if (-not (Test-Path $wrapper)) { Invoke-WebRequest -Uri $url -OutFile $wrapper -UseBasicParsing -ErrorAction Stop }
$actual = (Get-FileHash -LiteralPath $wrapper -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { Remove-Item $wrapper -Force; throw 'WinSW wrapper checksum mismatch. Installation stopped.' }
$escape = {param($v) [Security.SecurityElement]::Escape($v) }
$dataSafe = & $escape $DataDir
$exeSafe = & $escape $binary
$logSafe = & $escape (Join-Path $DataDir 'logs')
$remoteSafe = & $escape $RemoteAdminCIDRs
$tmdb = if ($EnableTMDB) { '1' } else { '0' }
$xml = @"
<service>
  <id>PlexCastExplorer</id><name>Plex Cast Explorer</name>
  <description>Plex cast directory for trusted LAN and VPN clients</description>
  <executable>$exeSafe</executable>
  <workingdirectory>$( & $escape $InstallDir )</workingdirectory>
  <startmode>Automatic</startmode><delayedAutoStart>true</delayedAutoStart>
  <serviceaccount><username>NT AUTHORITY\LocalService</username></serviceaccount>
  <env name="CAST_EXPLORER_DATA_DIR" value="$dataSafe" />
  <env name="CAST_EXPLORER_ENABLE_TMDB" value="$tmdb" />
  <env name="CAST_EXPLORER_REMOTE_ADMIN_CIDRS" value="$remoteSafe" />
  <logpath>$logSafe</logpath><log mode="roll" />
  <onfailure action="restart" delay="15 sec" />
  <stoptimeout>25 sec</stoptimeout>
</service>
"@
$xmlPath=Join-Path $InstallDir 'PlexCastExplorerService.xml'
[IO.File]::WriteAllText($xmlPath,$xml,[Text.UTF8Encoding]::new($false))
if ($RemoteAdminCIDRs) {
    $env:CAST_EXPLORER_DATA_DIR=$DataDir
    if (-not (Test-Path (Join-Path $DataDir 'admin_auth.json'))) {
        Write-Host 'Create your distinct administrator password (16+ characters).'
        & $binary --set-admin-password
        if ($LASTEXITCODE -ne 0) { throw 'Administrator password setup failed.' }
    }
}
& $wrapper install
if ($LASTEXITCODE -ne 0) { throw 'Windows service installation failed; see WinSW logs.' }
if ($AllowPrivateLanFirewall) {
    New-NetFirewallRule -DisplayName 'Plex Cast Explorer (private LAN only)' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -Profile Private -ErrorAction Stop | Out-Null
}
& $wrapper start
if ($LASTEXITCODE -ne 0) { throw 'Service installed but did not start. Check Windows Event Viewer and ProgramData logs.' }
Start-Sleep -Seconds 3
Get-Service PlexCastExplorer | Select-Object Name,Status,StartType
Write-Host "Service installed: http://127.0.0.1:8765"
Write-Host 'Existing original files were preserved. Verify gallery and indexing before deleting any old files.'
Write-Host 'Important: TMDB permissions, approved-logo attribution, and adult-content restrictions are the operator responsibility.'
if ($RemoteAdminCIDRs) { Write-Host 'Remote admin requires a VPN; browse /admin/login after gallery login from an allowed VPN client address.' }
