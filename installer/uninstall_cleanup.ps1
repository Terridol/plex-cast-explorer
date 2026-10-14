# Runs before Inno Setup removes program files. User library data is NEVER deleted.
$ErrorActionPreference = 'Stop'
$service = Get-Service -Name 'PlexCastExplorer' -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -ne 'Stopped') {
        Stop-Service -Name 'PlexCastExplorer' -Force
        (Get-Service -Name 'PlexCastExplorer').WaitForStatus('Stopped', [TimeSpan]::FromSeconds(30))
    }
    $wrapper = Join-Path $PSScriptRoot 'PlexCastExplorerService.exe'
    if (Test-Path -LiteralPath $wrapper) {
        & $wrapper uninstall
        if ($LASTEXITCODE -ne 0) { throw 'Unable to unregister PlexCastExplorer service.' }
    } else {
        & sc.exe delete PlexCastExplorer | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Unable to unregister PlexCastExplorer service.' }
    }
}
Get-NetFirewallRule -Name 'PlexCastExplorer-Inbound-Private' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallRule -DisplayName 'Plex Cast Explorer (private LAN only)' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Write-Host 'Uninstalled service and application rule; all ProgramData credentials, database and portraits were retained.'
