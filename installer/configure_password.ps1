param([switch]$Admin)
$ErrorActionPreference = 'Stop'
$elevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $elevated) {
    $params = '-NoProfile -ExecutionPolicy Bypass -File "' + $MyInvocation.MyCommand.Path + '"'
    if ($Admin) { $params += ' -Admin' }
    Start-Process -FilePath powershell.exe -ArgumentList $params -Verb RunAs -Wait
    exit
}
$env:CAST_EXPLORER_DATA_DIR = Join-Path $env:ProgramData 'PlexCastExplorer'
$app = Join-Path $PSScriptRoot 'PlexCastExplorer.exe'
if (!(Test-Path $app)) { throw 'Application executable not installed.' }
if ($Admin) { & $app --set-admin-password } else { & $app --set-password }
if ($LASTEXITCODE -ne 0) { throw 'Password configuration failed.' }
Write-Host 'Updated password. Existing sessions were invalidated.'
Read-Host 'Press Enter to close'
