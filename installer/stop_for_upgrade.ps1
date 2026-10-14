# Called BEFORE the new installer replaces executable files.
$ErrorActionPreference = 'Stop'
$svc = Get-Service -Name 'PlexCastExplorer' -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne 'Stopped') {
    Stop-Service -Name 'PlexCastExplorer' -Force
    (Get-Service -Name 'PlexCastExplorer').WaitForStatus('Stopped',[TimeSpan]::FromSeconds(30))
}
