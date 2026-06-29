#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# AI Automation Framework — One-shot setup script
# Works on: macOS, Linux, Windows Git Bash / WSL
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
if [ -t 1 ]; then           # Only colour when writing to a terminal
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  RED='\033[0;31m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  DIM='\033[2m'
  NC='\033[0m'
else
  GREEN='' YELLOW='' RED='' CYAN='' BOLD='' DIM='' NC=''
fi

ok()   { echo -e "  ${GREEN}[ok]${NC}    $*"; }
warn() { echo -e "  ${YELLOW}[warn]${NC}  $*"; }
fail() { echo -e "  ${RED}[error]${NC} $*" >&2; exit 1; }
step() { echo -e "  ${CYAN}→${NC} $*"; }
info() { echo -e "  ${DIM}        $*${NC}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BOLD}AI Automation Framework${NC}"
echo -e "  ${DIM}One-shot setup script${NC}"
echo ""

# ── Detect OS for platform-specific hints ────────────────────────────────────
OS="linux"
case "$OSTYPE" in
  darwin*)  OS="mac" ;;
  msys*|cygwin*|mingw*) OS="windows-bash" ;;
esac

# ── 1. Find Python 3.10+ ─────────────────────────────────────────────────────
step "Checking Python version..."

PYTHON_CMD=""
for cmd in python3 python python3.12 python3.11 python3.10; do
  if command -v "$cmd" &>/dev/null; then
    read -r MAJ MIN <<< "$("$cmd" -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2>/dev/null || echo "0 0")"
    if [ "$MAJ" -ge 3 ] && [ "$MIN" -ge 10 ]; then
      VER=$("$cmd" -c "import sys; print(sys.version.split()[0])")
      PYTHON_CMD="$cmd"
      ok "Python $VER  ($cmd)"
      break
    fi
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  fail "Python 3.10+ not found. Install from https://python.org/downloads/"
fi

# ── 2. Create virtual environment ─────────────────────────────────────────────
step "Checking virtual environment..."

VENV_PIP=".venv/bin/pip"
VENV_PYTHON=".venv/bin/python"
VENV_PLAYWRIGHT=".venv/bin/playwright"
VENV_FRAMEWORK=".venv/bin/framework"

# Windows Git Bash / MSYS uses Scripts instead of bin
if [ "$OS" = "windows-bash" ]; then
  VENV_PIP=".venv/Scripts/pip"
  VENV_PYTHON=".venv/Scripts/python"
  VENV_PLAYWRIGHT=".venv/Scripts/playwright"
  VENV_FRAMEWORK=".venv/Scripts/framework"
fi

if [ -d ".venv" ]; then
  ok ".venv already exists — skipping creation"
else
  step "Creating .venv..."
  "$PYTHON_CMD" -m venv .venv
  ok ".venv created"
fi

# ── 3. Install framework + dependencies ───────────────────────────────────────
step "Installing framework dependencies  (pip install -e .)..."

"$VENV_PIP" install -e . --quiet --disable-pip-version-check || {
  warn "Quiet install failed — retrying with full output"
  "$VENV_PIP" install -e .
}
ok "Dependencies installed"

# ── 4. Install Playwright Chromium ────────────────────────────────────────────
step "Installing Playwright Chromium browser..."

# Check if Chromium is already usable — avoids a slow re-download on re-runs
BROWSER_OK=false
if "$VENV_PYTHON" -c "
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        p.chromium.launch(headless=True).close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
  BROWSER_OK=true
fi

if [ "$BROWSER_OK" = true ]; then
  ok "Playwright Chromium already installed"
else
  "$VENV_PLAYWRIGHT" install chromium
  ok "Playwright Chromium ready"
fi

# ── 5. Check Allure CLI (optional) ────────────────────────────────────────────
step "Checking for Allure CLI (optional)..."

if command -v allure &>/dev/null; then
  ALLURE_VER=$(allure --version 2>/dev/null || echo "unknown version")
  ok "Allure $ALLURE_VER found — full interactive dashboard enabled"
else
  warn "Allure CLI not installed — framework will use fallback HTML report"
  if [ "$OS" = "mac" ]; then
    info "brew install allure          (requires Java)"
  elif [ "$OS" = "linux" ]; then
    info "sudo apt-get install allure  OR  snap install allure"
  else
    info "scoop install allure  (Windows — requires Java)"
  fi
fi

# ── 6. Clean leftover run artifacts ───────────────────────────────────────────
step "Cleaning leftover run artifacts..."

if [ -f "$VENV_FRAMEWORK" ]; then
  "$VENV_FRAMEWORK" clean --yes 2>/dev/null && ok "Artifacts cleaned" || warn "clean skipped (no artifacts)"
else
  warn "framework CLI not found at $VENV_FRAMEWORK — skipping clean"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${GREEN}${BOLD}✓ Setup complete!${NC}"
echo ""
echo -e "  ${BOLD}NEXT STEPS${NC}"
echo ""
echo -e "  1. Activate the virtual environment:"
if [ "$OS" = "windows-bash" ]; then
  echo -e "     ${YELLOW}source .venv/Scripts/activate${NC}"
else
  echo -e "     ${YELLOW}source .venv/bin/activate${NC}"
fi
echo ""
echo -e "  2. Configure your application:"
echo -e "     ${YELLOW}framework setup${NC}"
echo ""
echo -e "  3. Add test stories:"
echo -e "     ${YELLOW}framework add-story --text \"As a user I want to log in\"${NC}"
echo ""
echo -e "  4. Generate + run tests:"
echo -e "     ${YELLOW}framework build${NC}"
echo -e "     ${YELLOW}framework run --headless${NC}"
echo ""
echo -e "  ${DIM}Or open your IDE and tell the agent:${NC}"
echo -e "  ${CYAN}\"I want to test [your app URL]\"${NC}"
echo ""
