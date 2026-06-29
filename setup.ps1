#Requires -Version 5.1
<#
.SYNOPSIS
    One-shot setup for the AI Automation Framework.

.DESCRIPTION
    - Checks Python 3.10+
    - Creates .venv (skips if already exists)
    - Installs all Python dependencies  (pip install -e .)
    - Installs Playwright Chromium browser
    - Checks for optional Allure CLI
    - Cleans any leftover run artifacts

.USAGE
    # From the repo root in PowerShell:
    powershell -ExecutionPolicy Bypass -File setup.ps1

    # Or if your policy already allows scripts:
    .\setup.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -- Helpers ------------------------------------------------------------------

function Write-Step  { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "  [ok]     $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  [warn]   $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  [error]  $msg" -ForegroundColor Red }
function Write-Info  { param($msg) Write-Host "           $msg" -ForegroundColor DarkGray }

# -- Banner -------------------------------------------------------------------

Write-Host ""
Write-Host "  AI Automation Framework" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host "  One-shot setup script" -ForegroundColor DarkGray
Write-Host ""

# -- 1. Find Python 3.10+ -----------------------------------------------------

Write-Step "Checking Python version..."

$pythonExe = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $raw = & $cmd -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2>$null
        if ($raw) {
            $parts = $raw.Trim().Split(" ")
            $maj = [int]$parts[0]; $min = [int]$parts[1]
            if ($maj -ge 3 -and $min -ge 10) {
                $ver = & $cmd -c "import sys; print(sys.version.split()[0])" 2>$null
                $pythonExe = $cmd
                Write-Ok "Python $ver found  ($cmd)"
                break
            } else {
                Write-Warn "Python $maj.$min found via '$cmd' but 3.10+ is required - trying next"
            }
        }
    } catch { }
}

if (-not $pythonExe) {
    Write-Fail "Python 3.10+ not found."
    Write-Info  "Download from https://python.org/downloads/"
    Write-Info  "On Windows you can also: winget install Python.Python.3.12"
    exit 1
}

# -- 2. Create virtual environment --------------------------------------------

Write-Step "Checking virtual environment..."

$venvPip        = ".\.venv\Scripts\pip.exe"
$venvPlaywright = ".\.venv\Scripts\playwright.exe"
$venvFramework  = ".\.venv\Scripts\framework.exe"
$venvPython     = ".\.venv\Scripts\python.exe"

if (Test-Path ".venv") {
    Write-Ok ".venv already exists - skipping creation"
} else {
    Write-Step "Creating .venv..."
    & $pythonExe -m venv .venv
    Write-Ok ".venv created"
}

# -- 3. Install framework + dependencies --------------------------------------

Write-Step "Installing framework dependencies (pip install -e .)..."

& $venvPip install -e . --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
    & $venvPip install -e .
    if ($LASTEXITCODE -ne 0) { Write-Fail "pip install failed. See output above."; exit 1 }
}
Write-Ok "Dependencies installed"

# -- 4. Install Playwright Chromium -------------------------------------------

Write-Step "Installing Playwright Chromium browser..."

$playwrightInstalled = $false
if (Test-Path $venvPlaywright) {
    $browserCheck = & $venvPython -c "
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        p.chromium.launch(headless=True).close()
    print('ok')
except:
    print('missing')
" 2>$null
    if ($browserCheck -eq "ok") {
        Write-Ok "Playwright Chromium already installed"
        $playwrightInstalled = $true
    }
}

if (-not $playwrightInstalled) {
    & $venvPlaywright install chromium
    if ($LASTEXITCODE -ne 0) { Write-Fail "playwright install chromium failed."; exit 1 }
    Write-Ok "Playwright Chromium ready"
}

# -- 5. Check Allure CLI (optional) -------------------------------------------

Write-Step "Checking for Allure CLI (optional)..."

if (Get-Command "allure" -ErrorAction SilentlyContinue) {
    $allureVer = (allure --version 2>$null) -replace "allure ", ""
    Write-Ok "Allure $allureVer found - full interactive dashboard enabled"
} else {
    Write-Warn "Allure CLI not installed - framework will use fallback HTML report"
    Write-Info  "To enable the full Allure dashboard (requires Java):"
    Write-Info  "  scoop install allure          (recommended - https://scoop.sh)"
    Write-Info  "  choco install allure          (if you use Chocolatey)"
}

# -- 6. Clean leftover artifacts ----------------------------------------------

Write-Step "Cleaning leftover run artifacts..."

if (Test-Path $venvFramework) {
    & $venvFramework clean --yes 2>$null
    Write-Ok "Artifacts cleaned"
} else {
    Write-Warn "framework CLI not found at $venvFramework - skipping clean"
}

# -- Done ---------------------------------------------------------------------

Write-Host ""
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  NEXT STEPS" -ForegroundColor White
Write-Host ""
Write-Host "  1. Activate the virtual environment:" -ForegroundColor DarkGray
Write-Host "       .venv\Scripts\activate" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Configure your application:" -ForegroundColor DarkGray
Write-Host "       framework setup" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Add test stories:" -ForegroundColor DarkGray
Write-Host "       framework add-story --text" -ForegroundColor Yellow
Write-Host ""
Write-Host "  4. Generate + run tests:" -ForegroundColor DarkGray
Write-Host "       framework build" -ForegroundColor Yellow
Write-Host "       framework run --headless" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Or open your IDE and tell the AI agent what you want to test." -ForegroundColor DarkGray
Write-Host ""
