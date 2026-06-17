# AI-Augmented Test Automation Framework

A production-grade Python test automation framework with native AI integration via:
- **Model Context Protocol (MCP)** — live DOM inspection and exploratory probing for IDE agents
- **Custom CLI** — code generation from user stories and test execution
- **Local Memory Engine** — persistent application context for self-healing test generation
- **Page Object Model** — Playwright-backed, typed, explicit-wait-first architecture

---

## Quick Start

### 1. Install dependencies

```bash
cd ai-automation-framework
pip install -e .
playwright install chromium
```

### 2. Configure your application

Edit `config.json`:
```json
{
  "app": { "base_url": "https://your-app.example.com" }
}
```

### 3. Explore a new page via the MCP server

Start the MCP server (IDE will connect to it):
```bash
python mcp_server/server.py
```

Then in your IDE agent, call:
```
probe_application_state("https://your-app.example.com/login")
```

### 4. Generate a Page Object + Locators

```bash
framework generate-page --url https://your-app.example.com/login
```
Produces:
- `pages/login_page.py` — typed POM class extending `BasePage`
- `locators/login_locators.py` — isolated CSS selector constants

### 5. Write a user story and generate tests

```bash
# Edit stories/my_story.json with your workflow steps
framework generate-test --story stories/my_story.json
```
Produces: `tests/workflows/test_my_story.py`

### 6. Run tests

```bash
# All tests, with HTML report
framework run

# Specific suite
framework run --suite tests/workflows/test_login_workflow.py

# Headed, with a specific browser
framework run --browser firefox

# Headless CI mode
framework run --headless
```

---

## Directory Structure

```
ai-automation-framework/
├── config.py / config.json        ← Framework & browser configuration
├── pyproject.toml                 ← Package definition & CLI entry point
│
├── core/
│   ├── base_page.py               ← Base POM class with explicit waits
│   ├── driver_factory.py          ← Playwright browser lifecycle
│   └── memory_engine.py           ← Persistent local knowledge store
│
├── cli/
│   └── commands.py                ← `framework` CLI (generate-page, generate-test, run, memory)
│
├── mcp_server/
│   ├── server.py                  ← FastMCP server exposing 5 tools to IDE agents
│   └── tools.py                   ← DOMInspector, ApplicationProber, MemoryTool
│
├── locators/                      ← Selector constants only — one file per page
├── pages/                         ← Page Object classes — one file per page
├── tests/
│   ├── conftest.py                ← Pytest fixtures, failure hooks, CLI options
│   └── workflows/                 ← Test suites — one file per user story
│
├── services/
│   └── api_service.py             ← Backend HTTP client for data setup/teardown
│
├── utils/
│   └── helpers.py                 ← StoryParser, CodeGenerator
│
├── stories/                       ← User story JSON files (source of truth)
├── memory/                        ← Auto-managed JSON knowledge store
└── reports/                       ← HTML reports and failure screenshots
```

---

## MCP Server Tools

The server exposes 5 tools to IDE AI agents:

| Tool | Purpose |
|---|---|
| `probe_application_state(url)` | Map all interactive elements, forms, and navigation on a page |
| `inspect_current_dom(url, selector)` | Inspect specific elements with live attribute and bounding-box data |
| `read_local_memory(query, category)` | Retrieve stored quirks, selector fixes, workflow patterns |
| `write_local_memory(key, value, category, tags)` | Persist new application knowledge |
| `record_selector_fix(page, element, original, fixed, reason)` | Log selector corrections for self-healing |

### Add to Claude Code (`.claude/mcp.json`)

```json
{
  "mcpServers": {
    "ai-automation": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "/path/to/ai-automation-framework"
    }
  }
}
```

---

## CLI Reference

```bash
framework generate-page --url <url> [--name <ClassName>] [--output-dir pages/]
framework generate-test  --story <path.json> [--output-dir tests/workflows/]
framework run            [--suite <path>] [--browser chromium|firefox|webkit]
                         [--headless] [--base-url <url>] [-k <keyword>]
framework memory         --action show|search|clear [--query <text>]
```

---

## User Story Schema

```json
{
  "id": "my_story_001",
  "title": "Human-readable title",
  "description": "As a ... I want to ... so that ...",
  "priority": "high | critical | medium | low",
  "tags": ["smoke", "regression"],
  "pages": ["LoginPage"],
  "preconditions": ["..."],
  "steps": [
    {
      "id": "step_01",
      "action": "navigate | fill | click | assert_url | assert_visible | assert_text | select",
      "target": "CSS selector or URL path",
      "value": "Input value (for fill/assert_text/select)",
      "description": "Human-readable step description"
    }
  ],
  "expected_outcomes": ["..."],
  "negative_scenarios": [
    {
      "id": "neg_01",
      "title": "Scenario title",
      "steps": ["..."],
      "expected": "Expected outcome"
    }
  ]
}
```

---

## Architecture Principles

1. **Selectors in Locators only** — never inline a CSS string in a page method or test
2. **Explicit waits always** — `BasePage.wait_for_element()` wraps every interaction
3. **Memory first** — query local memory before writing any test or locator
4. **CLI for scaffolding** — use `generate-page` and `generate-test`, never write boilerplate manually
5. **MCP for exploration** — probe and inspect live; never guess DOM structure
6. **Failures self-heal** — `record_selector_fix` updates memory so generation improves over time

---

## Pytest Options

```bash
pytest tests/ --browser-type chromium --headless --base-url https://staging.app.com
pytest tests/ -k "smoke" --html reports/report.html --self-contained-html
```

---

## Tech Stack

| Component | Library |
|---|---|
| Browser automation | Playwright (`playwright`, `pytest-playwright`) |
| Test runner | pytest + pytest-html |
| MCP server | FastMCP |
| CLI | Click |
| Memory store | stdlib JSON (no external DB) |
| Python | 3.10+ with full type annotations |
