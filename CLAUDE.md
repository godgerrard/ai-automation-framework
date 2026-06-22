# AI Automation Framework — Contribution Guidelines

## Loop stop rules

The agent loops until one of these is true:

- **All green** — every test passes. Stop and report success with pytest output proof.
- **5 cycles used** — stop. Report what still fails and what was tried.
- **Same failure twice in a row** — stop. The failure is an application bug, not a selector bug.
- **A fix causes a passing test to fail** — stop. Revert the fix. Escalate to the user.

Never report success without showing actual pytest output from the final run.
Never weaken or delete an assertion to make a test pass — fix the locator or file the bug.

---

## What this repo IS

A reusable, client-agnostic test automation framework built on Playwright + pytest.
It ships the **engine** — page base classes, API client, memory engine, MCP server,
CLI, and code generators. It does NOT ship test suites for any specific application.

The primary interface is the AI agent. Users talk to their IDE agent in plain English.
The agent drives the CLI and MCP tools. Users never write test code directly.

---

## What belongs in git (framework engine)

```
core/              BasePage, MemoryEngine, DriverFactory
services/          APIService, APIResponse (fluent assertions)
cli/               All `framework` commands
utils/             NaturalLanguageStoryParser, AutoDOMMapper, DOMProber,
                   AllureTestGenerator, CodeGenerator, ProjectScaffolder
mcp_server/        FastMCP server + DOM inspection tools
tests/conftest.py  Framework-level pytest fixtures only
tests/unit/        Framework engine unit tests (no browser, always committable)
config.py          Configuration loader
pyproject.toml     Build manifest and CLI entry point
stories/templates/ Reference story templates (read-only)
.claude/agents/    Loop agent instruction files
.claude/commands/  /loop orchestration command
.mcp.json          MCP server config for Claude Code auto-discovery
copilot-instructions.md  Agent operating protocol
```

---

## What does NOT belong in git (project-specific)

Generated per target application. Listed in `.gitignore`. Never commit these.

| Pattern | Contents |
|---|---|
| `locators/[!_]*.py` | Selector constants for a specific app |
| `pages/[!_]*.py` | Page Object classes for a specific app |
| `tests/workflows/test_*.py` | UI test suites for a specific app |
| `tests/api/test_*.py` | API test suites for a specific app |
| `stories/*.json` | Parsed user stories for a specific app |
| `allure-results/` | Raw Allure JSON from test runs |
| `allure-report/` | Generated HTML dashboard |
| `bugs.md` | Application bug report |
| `memory/framework_memory.json` | Runtime self-healing data |
| `.env` | Credentials — never committed |

---

## Starting a new project (agent flow)

The agent handles this automatically when the user says "test my app".
For manual or CI use:

```bash
# Interactive wizard (prompts for URL, credentials, browser)
framework setup

# Non-interactive (CI / scripted)
framework setup \
  --non-interactive \
  --url https://yourapp.com \
  --name yourapp \
  --username testuser \
  --password testpass \
  --browser chromium

# Add stories from plain English
framework add-story --text "As a user I want to log in and see the dashboard"
framework add-story --file requirements.txt

# Probe live DOM and generate all test code
framework build

# Run tests with Allure reporting
framework run --headless

# Fix a broken locator (Corrector loop)
framework fix-selector \
  --file locators/yourapp_locators.py \
  --constant LOGIN_BUTTON \
  --selector "[data-test='login-btn']"
```

---

## Code style

- Page Objects in `pages/`, extend `BasePage`
- Locators in `locators/`, pure string constants — no logic
- Tests use pytest classes; always include the `memory` fixture parameter
- `[data-test='...']` preferred; never use positional selectors or XPath unless unavoidable
- API tests use `APIResponse` fluent assertions — never bare `assert resp.status_code == 200`

---

## Full agent protocol

See `copilot-instructions.md` for the complete conversation flow, four-loop
definitions, bug classification logic, selector priority rules, and token budget.
