# Mandatory parse gate for Windows installer/service/updater PowerShell scripts.
# This script only parses files; it does not execute them.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$paths = @('build_installer_windows.ps1', 'build_windows_exe.ps1',
           'installer/configure_service.ps1', 'installer/stop_for_upgrade.ps1',
           'installer/uninstall_cleanup.ps1', 'installer/configure_password.ps1',
           'installer/check_updates.ps1')
$failed = $false
foreach ($relative in $paths) {
    $file = Join-Path $root $relative
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        Write-Host "[FAIL] Missing PowerShell file: $relative"
        $failed = $true
        continue
    }
    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $file, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count -gt 0) {
        Write-Host "[FAIL] PowerShell syntax: $relative"
        foreach ($errorItem in $parseErrors) { Write-Host ($errorItem.ToString()) }
        $failed = $true
    } else {
        Write-Host "[PASS] PowerShell syntax: $relative"
    }
}
if ($failed) { exit 1 }
exit 0