# Mandatory PowerShell parse gate. Discover every tracked production script
# in the root, installer and scripts directories (including this gate).
# Parse only; never execute the installer or modify a running service.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$directories = @($root, (Join-Path $root 'installer'), (Join-Path $root 'scripts'))
$paths = @(
    foreach ($directory in $directories) {
        if (Test-Path -LiteralPath $directory -PathType Container) {
            Get-ChildItem -LiteralPath $directory -Filter '*.ps1' -File
        }
    }
)
if ($paths.Count -eq 0) {
    Write-Host '[FAIL] No PowerShell scripts found for syntax validation.'
    exit 1
}
$failed = $false
foreach ($entry in $paths) {
    $relative = $entry.FullName.Substring($root.Length + 1)
    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $entry.FullName, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count -gt 0) {
        Write-Host "[FAIL] PowerShell syntax: $relative"
        foreach ($errorItem in $parseErrors) { Write-Host ($errorItem.ToString()) }
        $failed = $true
    } else {
        Write-Host "[PASS] PowerShell syntax: $relative"
    }
}
if ($failed) { exit 1 }
Write-Host "[PASS] Parsed $($paths.Count) PowerShell scripts."
exit 0
