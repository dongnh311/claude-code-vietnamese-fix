#
# Claude Code Vietnamese IME Fix - Installer (Windows)
# Clone repo va chay interactive menu
#
# Usage:
#   irm https://raw.githubusercontent.com/dongnh311/claude-code-vietnamese-fix/main/install.ps1 | iex
#

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/dongnh311/claude-code-vietnamese-fix.git"
$InstallDir = Join-Path $env:USERPROFILE ".claude-vn-fix"

Write-Host ""
Write-Host "Claude Code Vietnamese IME Fix - Installer"
Write-Host ""

# Check git
$gitExists = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitExists) {
    Write-Host "[ERROR] git khong tim thay" -ForegroundColor Red
    Write-Host "Cai dat: https://git-scm.com/downloads"
    exit 1
}

# Check python
$PythonCmd = $null
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $null = & $cmd --version 2>&1
        $PythonCmd = $cmd
        break
    } catch {}
}

if (-not $PythonCmd) {
    Write-Host "[ERROR] Python khong tim thay" -ForegroundColor Red
    Write-Host "Cai dat: https://python.org/downloads"
    exit 1
}

# Clone or update
Write-Host "-> Cai dat vao $InstallDir..."
if (Test-Path $InstallDir) {
    Set-Location $InstallDir
    # Update remote URL if it changed (e.g. fork migration)
    $CurrentUrl = git remote get-url origin 2>$null
    if ($CurrentUrl -ne $RepoUrl) {
        Write-Host "   Updating remote: $RepoUrl"
        git remote set-url origin $RepoUrl
    }
    try { git pull origin main 2>&1 | Out-Null } catch {}
} else {
    git clone --depth 1 $RepoUrl $InstallDir
}
Write-Host "   Done"
Write-Host ""

# Run interactive menu
Set-Location $InstallDir
& $PythonCmd patcher.py

Write-Host ""
Write-Host "================================================"
Write-Host "Commands:"
Write-Host "  Menu:    $PythonCmd $InstallDir\patcher.py"
Write-Host "  Auto:    $PythonCmd $InstallDir\patcher.py --auto"
Write-Host "  Restore: $PythonCmd $InstallDir\patcher.py --restore"
Write-Host "  Scan:    $PythonCmd $InstallDir\patcher.py --scan"
Write-Host "  Update:  cd $InstallDir; git pull"
Write-Host "================================================"
Write-Host ""
