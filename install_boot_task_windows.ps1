# OPTIONAL: Run as Administrator. Starts at Windows BOOT using LocalSystem.
# Python must be installed for all users, not under the user's private AppData.
# This is a background Scheduled Task, NOT a native Windows service.
$ErrorActionPreference = 'Stop'
$admin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw 'Run this script as Administrator.' }
$folder = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $folder 'app.py'
if (Get-Command py -ErrorAction SilentlyContinue) { $python = & py -3 -c 'import sys; print(sys.executable)' 2>$null }
if (-not $python -and (Get-Command python -ErrorAction SilentlyContinue)) { $python = & python -c 'import sys; print(sys.executable)' }
if (-not $python -or -not (Test-Path $python)) { throw 'Python 3.10+ was not found.' }
$python = $python.Trim()
if ($python -match '(?i)\\Users\\[^\\]+\\AppData\\') {
    throw 'This is a per-user Python installation, which SYSTEM may not be able to access. Install Python for all users, then run again.'
}
$pythonW = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
if (Test-Path $pythonW) { $python = $pythonW }
$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '"') -WorkingDirectory $folder
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName 'PlexCastExplorer' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Plex Cast Explorer background server started at boot' -Force | Out-Null
Start-ScheduledTask -TaskName 'PlexCastExplorer'
Write-Host 'Installed PlexCastExplorer to start as SYSTEM at Windows boot.'
Write-Host 'Do not also use the sign-in task or the manual start_windows.bat launcher.'
Write-Host 'Check server.log and Task Scheduler history if the service does not start.'
