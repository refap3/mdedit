# One-line install (run in PowerShell):
#   irm https://raw.githubusercontent.com/refap3/mdedit/main/install.ps1 | iex
#
# Or with a custom install directory:
#   $env:MDEDIT_DIR="C:\tools\mdedit"; irm https://raw.githubusercontent.com/refap3/mdedit/main/install.ps1 | iex

$ErrorActionPreference = 'Stop'

$Dest = if ($env:MDEDIT_DIR) { $env:MDEDIT_DIR } else { "$env:USERPROFILE\mdedit" }
$Venv = "$Dest\.venv"
# WindowsApps is always in PATH - no PATH manipulation needed
$BinDir = "$env:LOCALAPPDATA\Microsoft\WindowsApps"

# Already installed? Still repair launcher in case it is missing.
$alreadyInstalled = Test-Path "$Dest\.git"
if ($alreadyInstalled) {
    Write-Host "MDEdit already installed at $Dest - repairing launcher ..."
}

# Check for git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git not found. Install Git for Windows from https://git-scm.com and re-run."
    exit 1
}

# Find Python 3.10+ (try py launcher, then python, then python3)
$Python = $null
foreach ($cmd in @('py', 'python', 'python3')) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $ver = & $cmd --version 2>&1
        if ($ver -match '(\d+)\.(\d+)' -and [int]$Matches[1] -ge 3 -and [int]$Matches[2] -ge 10) {
            $Python = $cmd
            break
        }
    }
}
if (-not $Python) {
    Write-Error "Python 3.10+ not found. Install from https://www.python.org and re-run."
    exit 1
}

if (-not $alreadyInstalled) {
    # Clone
    Write-Host "Cloning mdedit into $Dest ..."
    git clone --depth 1 https://github.com/refap3/mdedit "$Dest"

    # Virtual environment
    Write-Host "Creating virtual environment ..."
    & $Python -m venv "$Venv"

    # Dependencies
    Write-Host "Installing dependencies ..."
    & "$Venv\Scripts\pip.exe" install -q --upgrade pip
    & "$Venv\Scripts\pip.exe" install -q -r "$Dest\requirements.txt"
}

# Launchers in WindowsApps (always on PATH, no registry changes needed)
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# mdedit.bat for CMD / PowerShell
$batLines = '@echo off', "`"$Venv\Scripts\python.exe`" `"$Dest\mdedit.py`" %*"
[System.IO.File]::WriteAllLines("$BinDir\mdedit.bat", $batLines, [System.Text.Encoding]::ASCII)

# mdedit-update.bat for CMD / PowerShell
$updateBatLines = '@echo off', "powershell -ExecutionPolicy Bypass -File `"$Dest\update.ps1`""
[System.IO.File]::WriteAllLines("$BinDir\mdedit-update.bat", $updateBatLines, [System.Text.Encoding]::ASCII)

# shell scripts for Git Bash (LF line endings, no extension)
$shLines = '#!/usr/bin/env bash', "exec `"$($Venv.Replace('\','/'))/Scripts/python.exe`" `"$($Dest.Replace('\','/'))/mdedit.py`" `"`$@`""
[System.IO.File]::WriteAllLines("$BinDir\mdedit", $shLines, (New-Object System.Text.UTF8Encoding $false))
$shUpdateLines = '#!/usr/bin/env bash', "exec bash `"$($Dest.Replace('\','/'))/update.sh`""
[System.IO.File]::WriteAllLines("$BinDir\mdedit-update", $shUpdateLines, (New-Object System.Text.UTF8Encoding $false))

Write-Host "Launcher: $BinDir\mdedit.bat"
Write-Host ""
Write-Host "Done. Run: mdedit [file.md]"
