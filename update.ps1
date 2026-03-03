# Update MDEdit to the latest version.
# Usage: & "$env:USERPROFILE\mdedit\update.ps1"

$ErrorActionPreference = 'Stop'

$Dest = if ($env:MDEDIT_DIR) { $env:MDEDIT_DIR } else { "$env:USERPROFILE\mdedit" }
$Venv = "$Dest\.venv"

if (-not (Test-Path "$Dest\.git")) {
    Write-Error "MDEdit not found at $Dest`nInstall first:`n  irm https://raw.githubusercontent.com/refap3/mdedit/main/install.ps1 | iex"
    exit 1
}

Write-Host "Updating MDEdit ..."
git -C "$Dest" pull

Write-Host "Updating dependencies ..."
& "$Venv\Scripts\pip.exe" install -q --upgrade pip
& "$Venv\Scripts\pip.exe" install -q -r "$Dest\requirements.txt"

$commit = git -C "$Dest" log -1 --format='%h — %s'
Write-Host ""
Write-Host "Done. $commit"
