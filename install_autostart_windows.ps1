# Installs a background Scheduled Task that runs Cast Explorer at user sign-in.
$ErrorActionPreference = 'Stop'
$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $folder 'app.py'
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = & py -3 -c 'import sys; print(sys.executable)' 2>$null
} 
if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $python = & python -c 'import sys; print(sys.executable)'
}
if (-not $python -or -not (Test-Path $python)) { throw 'Python 3.10+ was not found.' }
$pythonW = Join-Path (Split-Path -Parent $python.Trim()) 'pythonw.exe'
if (Test-Path $pythonW) { $python = $pythonW }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '"') -WorkingDirectory $folder
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PlexCastExplorer' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Plex Cast Explorer LAN browser' -Force | Out-Null
Start-ScheduledTask -TaskName 'PlexCastExplorer'
Write-Host 'Installed PlexCastExplorer to start automatically when this Windows user signs in.'
Write-Host 'You can verify it under Task Scheduler > Task Scheduler Library.'
Write-Host 'Check server.log for status. This mode starts at sign-in, not before sign-in.'
