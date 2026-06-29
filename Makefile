# ─────────────────────────────────────────────────────────────────────────────
# AI Automation Framework — Makefile
# Works on: macOS, Linux, Windows (Git Bash / WSL)
# Usage: make <target>
# ─────────────────────────────────────────────────────────────────────────────

# Auto-detect OS; use the correct venv path
ifeq ($(OS),Windows_NT)
  VENV_BIN   := .venv/Scripts
  PYTHON     := python
  SEP        := \\
else
  VENV_BIN   := .venv/bin
  PYTHON     := python3
  SEP        := /
endif

PIP         := $(VENV_BIN)/pip
FW          := $(VENV_BIN)/framework
PYTEST      := $(VENV_BIN)/pytest
PLAYWRIGHT  := $(VENV_BIN)/playwright

.DEFAULT_GOAL := help

# ── Help ─────────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  AI Automation Framework — available targets"
	@echo ""
	@echo "  Setup"
	@echo "    make setup          Full first-time setup (venv + deps + browser)"
	@echo "    make install        Reinstall framework deps only (no browser)"
	@echo ""
	@echo "  Development"
	@echo "    make test-unit      Run framework engine unit tests (no browser)"
	@echo "    make lint           Syntax-check all tracked Python files"
	@echo "    make clean          Wipe run artifacts (allure-results, reports, memory)"
	@echo ""
	@echo "  Run"
	@echo "    make build          Generate tests from all stories in stories/"
	@echo "    make run            Run full test suite headlessly"
	@echo "    make run-headed     Run full test suite in headed (visible) browser"
	@echo ""

# ── Setup ────────────────────────────────────────────────────────────────────
.PHONY: setup
setup: _venv install _playwright _clean-artifacts
	@echo ""
	@echo "  Setup complete."
	@echo ""
	@echo "  Activate:  source $(VENV_BIN)/activate"
	@echo "  Then run:  framework setup"
	@echo ""

.PHONY: _venv
_venv:
	@if [ ! -d ".venv" ]; then \
	  echo "  Creating .venv..."; \
	  $(PYTHON) -m venv .venv; \
	  echo "  .venv created"; \
	else \
	  echo "  .venv already exists"; \
	fi

.PHONY: install
install:
	@echo "  Installing dependencies..."
	$(PIP) install -e . --quiet --disable-pip-version-check
	@echo "  Done"

.PHONY: _playwright
_playwright:
	@echo "  Installing Playwright Chromium..."
	$(PLAYWRIGHT) install chromium
	@echo "  Done"

# ── Clean ────────────────────────────────────────────────────────────────────
.PHONY: clean _clean-artifacts
clean: _clean-artifacts

_clean-artifacts:
	@echo "  Cleaning run artifacts..."
	@$(FW) clean --yes 2>/dev/null || true
	@echo "  Done"

# ── Tests ────────────────────────────────────────────────────────────────────
.PHONY: test-unit
test-unit:
	@echo "  Running framework unit tests..."
	$(PYTEST) tests/unit/ -q --tb=short
	@echo ""

.PHONY: lint
lint:
	@echo "  Syntax-checking tracked Python files..."
	@find core cli utils services mcp_server -name "*.py" \
	  | xargs $(VENV_BIN)/python -m py_compile && echo "  All OK"

# ── Build & Run ───────────────────────────────────────────────────────────────
.PHONY: build
build:
	$(FW) build

.PHONY: run
run:
	$(FW) run --headless

.PHONY: run-headed
run-headed:
	$(FW) run

