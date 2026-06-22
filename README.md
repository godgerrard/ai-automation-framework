# AI Automation Framework

A production-grade test automation framework designed to be driven by any AI agent.
Connect your IDE's AI assistant, describe what you want to test in plain English,
and get a fully generated, running test suite with a report — no manual coding required.

---

## How it works

You talk to your AI agent. The agent asks you three questions, then runs everything internally.

```
You        →  "I want to test my e-commerce site"
Agent      →  "What's the URL?"
You        →  "https://myshop.com"
Agent      →  "Does it need login? If so, share credentials."
You        →  "admin@myshop.com / test123"
Agent      →  "What flows should I test?"
You        →  "Login, add to cart, and full checkout"

           [Agent runs the pipeline silently]

Agent      →  "Done. 14 tests generated, 14 passed.
               Dashboard → allure-report/index.html"
```

The agent drives four internal loops — Generator, Tester, Corrector, Reporter —
using the framework's CLI and MCP tools. You never touch a test file.

---

## Supported AI agents

Any IDE that supports the Model Context Protocol:

| IDE / Agent | Status |
|---|---|
| Claude Code | Fully supported |
| Cursor | Fully supported |
| GitHub Copilot (VS Code) | Fully supported |
| Windsurf | Fully supported |
| Any MCP-compatible agent | Works |

---

## Installation

**Requirements:** Python 3.10+, Node.js (optional — for Allure CLI)

```bash
git clone https://github.com/godgerrard/ai-automation-framework.git
cd ai-automation-framework
pip install -e .
playwright install chromium
```

---

## Connect your AI agent (MCP setup)

The framework exposes an MCP server that your IDE connects to.
Pick your IDE below — copy the config, update the path, and restart.

### Claude Code

Create `.mcp.json` in the repo root (already included):

```json
{
  "mcpServers": {
    "ai-automation": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "."
    }
  }
}
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ai-automation": {
      "command": "python",
      "args": ["/absolute/path/to/ai-automation-framework/mcp_server/server.py"]
    }
  }
}
```

### GitHub Copilot (VS Code)

Create `.vscode/mcp.json` in the repo:

```json
{
  "servers": {
    "ai-automation": {
      "command": "python",
      "args": ["${workspaceFolder}/mcp_server/server.py"]
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "ai-automation": {
      "command": "python",
      "args": ["/absolute/path/to/ai-automation-framework/mcp_server/server.py"]
    }
  }
}
```

Once connected, open a chat with your AI agent in the repo folder and say:
**"I want to test [your app URL]"** — the agent takes it from there.

---

## What the agent does internally

The agent follows a four-loop pipeline defined in `copilot-instructions.md`:

```
Plain English requirements
         │
         ▼  Zero tokens — CLI only
┌──────────────────────┐
│  LOOP 1  GENERATOR   │  framework add-story + framework build
│                      │  Probes live DOM, maps selectors, writes test code
└──────────┬───────────┘
           │ generated tests
           ▼  Zero tokens — CLI only
┌──────────────────────┐
│  LOOP 2  TESTER      │  pytest --alluredir=allure-results
│                      │  Runs all tests, captures structured results
└──────────┬───────────┘
           │ failures only
           ▼  Tokens spent HERE — one MCP call per broken selector
┌──────────────────────┐
│  LOOP 3  CORRECTOR   │  inspect_current_dom → framework fix-selector
│                      │  Fixes selector bugs; documents app bugs
│  Max 5 cycles        │
└──────────┬───────────┘
           │
           ▼  Zero tokens — CLI only
┌──────────────────────┐
│  LOOP 4  REPORTER    │  allure generate + bugs.md
│                      │  Dashboard + structured bug report
└──────────────────────┘
```

Token usage is near-zero for passing suites. The Corrector loop is the only
place AI tokens are spent, and only when tests fail.

---

## CLI reference

The `framework` command is what the agent (and you) use directly.

```bash
# First-time setup — interactive wizard
framework setup

# Non-interactive (for agent use)
framework setup \
  --non-interactive \
  --url https://myapp.com \
  --name myapp \
  --username admin \
  --password secret \
  --browser chromium

# Convert plain English to story JSON
framework add-story --text "As a user I want to log in and see my dashboard"
framework add-story --file requirements.txt

# Probe DOM + generate locators, pages, and tests from all stories
framework build

# Build a single story
framework build --story stories/login_001.json

# Build without live DOM probing (offline / CI)
framework build --no-probe

# Run all tests with Allure results
framework run

# Run with options
framework run --suite tests/workflows/ --headless --marker smoke

# Patch a single broken locator (used by Corrector loop)
framework fix-selector \
  --file locators/myapp_locators.py \
  --constant LOGIN_BUTTON \
  --selector "[data-test='login-button']"

# Inspect and manage the self-healing memory
framework memory --action show
framework memory --action search --query "login"
framework memory --action clear
```

---

## MCP tools (used by the agent)

These are the tools your AI agent calls directly. You don't invoke them —
the agent does. They are documented here so you understand what the agent
is doing and can audit its behaviour.

| Tool | Purpose | Token cost |
|---|---|---|
| `probe_application_state(url)` | Map all interactive elements, forms, navigation on a page | ~800–1500 |
| `inspect_current_dom(url, selector)` | Inspect specific elements — tag, text, attributes, visibility | ~300–600 |
| `read_local_memory(query)` | Retrieve stored selector fixes and quirks | ~100 |
| `write_local_memory(key, value, category)` | Persist application knowledge | ~100 |
| `record_selector_fix(page, element, original, fixed, reason)` | Log a corrected selector | ~100 |

The agent reads `copilot-instructions.md` to know exactly when and how to call each tool.

---

## Directory structure

```
ai-automation-framework/
│
├── .mcp.json                      ← MCP server config (Claude Code auto-discovers)
├── .claude/
│   ├── agents/
│   │   ├── generator.md           ← Loop 1 agent instructions
│   │   ├── corrector.md           ← Loop 3 agent instructions
│   │   └── reporter.md            ← Loop 4 agent instructions
│   └── commands/
│       └── loop.md                ← /loop orchestration command
│
├── cli/
│   └── commands.py                ← All `framework` CLI commands
│
├── core/
│   ├── base_page.py               ← BasePage (Playwright, explicit waits, typed)
│   ├── driver_factory.py          ← Browser lifecycle management
│   └── memory_engine.py           ← Thread-safe JSON memory store
│
├── mcp_server/
│   ├── server.py                  ← FastMCP server — agent connects here
│   └── tools.py                   ← DOM inspector, prober, memory tools
│
├── services/
│   ├── api_service.py             ← HTTP client (requests-based)
│   └── api_response.py            ← Fluent assertion chain for API responses
│
├── utils/
│   └── helpers.py                 ← NaturalLanguageStoryParser, AutoDOMMapper,
│                                     DOMProber, AllureTestGenerator,
│                                     CodeGenerator, ProjectScaffolder
│
├── tests/
│   ├── conftest.py                ← Framework fixtures (page, browser, memory, api)
│   └── unit/                      ← Framework engine unit tests (206 tests, no browser)
│
├── stories/
│   └── templates/                 ← Reference story JSON templates
│
├── config.py                      ← Configuration loader (config.json + .env + env vars)
├── config.json                    ← Base URL and browser settings
├── pyproject.toml                 ← Dependencies and CLI entry point
├── copilot-instructions.md        ← Agent operating protocol (read this first)
└── CLAUDE.md                      ← Contribution guidelines and loop stop rules
│
│   ── Generated per project (gitignored) ──
├── locators/                      ← Selector constants (one file per page)
├── pages/                         ← Page Object classes (one file per page)
├── tests/workflows/               ← Generated UI test suites
├── tests/api/                     ← Generated API test suites
├── stories/*.json                 ← Parsed user stories
├── .env                           ← Credentials (never committed)
├── allure-results/                ← Raw Allure JSON
├── allure-report/                 ← HTML dashboard
└── bugs.md                        ← Application bug report
```

---

## Outputs

After a run, the agent delivers:

| Output | Location | Description |
|---|---|---|
| Test dashboard | `allure-report/index.html` | Pass/fail by feature, story, and severity |
| HTML report | `reports/report.html` | Self-contained pytest-html report |
| Bug report | `bugs.md` | Structured list of application bugs found |
| Selector memory | `memory/` | Self-healing store — improves future runs |

---

## Credential environment variables

`framework build` resolves credentials in this order — no arbitrary scanning:

| Priority | Variable | Example |
|---|---|---|
| 1. CLI flag | `--username` / `--password` | `framework build --username admin --password s3cret` |
| 2. Project-scoped | `<PROJECT>_USERNAME` / `<PROJECT>_PASSWORD` | `MYAPP_LOGIN_USERNAME=admin` |
| 3. Generic fallback | `FRAMEWORK_USERNAME` / `FRAMEWORK_PASSWORD` | works across all projects |

The project prefix is derived from the story file names (e.g. `myapp_login_001.json` → `MYAPP_LOGIN`).
The easiest option for most users: set `FRAMEWORK_USERNAME` and `FRAMEWORK_PASSWORD` in `.env`.

---

## For power users

You can use the CLI directly without an AI agent — useful for CI pipelines.

```bash
# Full pipeline against a new app
framework setup --non-interactive --url https://myapp.com --name myapp
framework add-story --file requirements.txt
framework build --username admin --password secret
framework run --headless --alluredir allure-results

# Re-run smoke tests only after a deploy
framework run --marker smoke --headless

# Fix a broken selector after a frontend change
framework fix-selector \
  --file locators/myapp_locators.py \
  --constant SUBMIT_BUTTON \
  --selector "[data-test='submit-btn']"
```

---

## Tech stack

| Component | Library / Version |
|---|---|
| Browser automation | Playwright 1.44+ |
| Test runner | pytest 8+ |
| Test report | pytest-html 4+ |
| Allure integration | allure-pytest 2.13+ |
| MCP server | FastMCP 2.0+ |
| CLI | Click 8+ |
| Memory store | stdlib JSON + filelock |
| Python | 3.10+ |

---

## Architecture principles

1. **CLI = generation. MCP = exploration.** Never swap them.
2. **Selectors live in locators only** — never inline a CSS string in page methods or tests.
3. **Memory first** — check local memory before probing the DOM; avoid duplicate MCP calls.
4. **`data-test` attributes preferred** — XPath only as a last resort.
5. **App bugs are documented, not hidden** — never weaken an assertion to reach green.
6. **Token efficiency** — a full passing run costs zero AI tokens.

---

## Agent protocol

The full agent conversation flow, loop definitions, bug classification logic,
selector priority rules, and token budget guidelines are in
**[copilot-instructions.md](copilot-instructions.md)**.

Read that file to understand exactly how the agent thinks and operates.
