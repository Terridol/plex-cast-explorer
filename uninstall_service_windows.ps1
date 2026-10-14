# Remove Windows service and binaries. Preserves ProgramData library state by default.
param([string]$InstallDir = "$env:ProgramFiles\PlexCastExplorer")
$ErrorActionPreference='Stop'
$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {throw 'Run PowerShell as Administrator.'}
$wrapper=Join-Path $InstallDir 'PlexCastExplorerService.exe'
if (-not (Test-Path $wrapper)) {throw "WinSW wrapper not found at $wrapper"}
& $wrapper stop
& $wrapper uninstall
if (Get-Service PlexCastExplorer -ErrorAction SilentlyContinue) {throw 'Service still registered; consult Event Viewer before removing files.'}
Write-Host 'Service removed. ProgramData data and portraits were preserved.'
Write-Host "Installed files remain at $InstallDir; remove manually only after checking your backups."
