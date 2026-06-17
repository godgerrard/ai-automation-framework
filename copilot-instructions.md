# Copilot Instructions for AI Automation Framework

You are operating inside an advanced AI-augmented test automation repository.
You have access to a **Custom Framework CLI** and a **FastMCP Server**.
You must triage every task through the decision matrix below before writing a single line of code.

---

## Triage Matrix

### 1. Exploratory Testing / Element Discovery

> **Trigger:** Any task involving a new page, unknown selector, or DOM behavior.

- **DO NOT** write blind locators or guess CSS selectors.
- **DO** call the MCP tool `probe_application_state(url)` **first** to map the full interactive element tree.
- **DO** call `inspect_current_dom(url, selector)` to validate a specific element's attributes before committing it to a Locator class.
- After discovery, record selector knowledge with `write_local_memory`.

### 2. Code Generation & Boilerplate Setup

> **Trigger:** Creating a new Page Object class, Locator file, or test suite.

- **DO NOT** write POM classes or pytest files manually from scratch.
- **DO** invoke the Framework CLI:
  ```bash
  # Generate a Page class + Locator file skeleton
  framework generate-page --url https://app.example.com/login

  # Generate a full pytest test class from a user story
  framework generate-test --story stories/login_user_story.json
  ```
- The CLI produces correctly structured, import-correct Python that matches the repo's conventions.

### 3. Contextual Awareness (Memory-First)

> **Trigger:** Before modifying OR creating any test or locator.

- **DO** call `read_local_memory(query="<page or element name>")` before writing any code.
- The memory engine stores:
  - Known selector quirks (e.g., dynamic IDs, shadow DOM)
  - Behavioral anti-patterns (e.g., "avoid clicking banner ad during checkout")
  - Self-healing corrections from prior test failures
- If you discover a new quirk, **immediately** persist it with `write_local_memory`.
- If you correct a selector, **always** call `record_selector_fix` so future generation is self-healing.

---

## Repository Layout Reference

```
ai-automation-framework/
├── core/
│   ├── base_page.py        ← Extend this for every Page Object
│   ├── driver_factory.py   ← Browser lifecycle (do not instantiate Playwright directly)
│   └── memory_engine.py    ← Local knowledge store API
├── cli/commands.py         ← CLI entry point (run as: framework <command>)
├── mcp_server/server.py    ← MCP server (tools exposed to IDE agents)
├── locators/               ← ONE file per page, ONLY selectors (no logic)
├── pages/                  ← ONE file per page, ONLY actions + assertions (no selectors inline)
├── tests/workflows/        ← Pytest test classes (one per user story)
├── services/api_service.py ← Use for API-level test data setup, not UI actions
├── stories/                ← Source-of-truth user story files (.json)
└── memory/                 ← Auto-managed; do not edit directly
```

---

## Separation of Concerns (Non-Negotiable)

| Layer | Responsibility | Forbidden |
|---|---|---|
| `locators/` | CSS/XPath strings only | Any logic, imports from `pages/` |
| `pages/` | Actions + assertions using BasePage methods | Inline selector strings |
| `tests/` | Assertions + fixture orchestration | Direct Playwright API calls |
| `services/` | API HTTP calls only | Playwright / browser code |
| `core/` | Framework infrastructure | Business-domain logic |

---

## Coding Standards

- **Python 3.10+** with full type annotations (`from __future__ import annotations`)
- All Page Objects **must** extend `BasePage` — never call `page.locator()` directly in a test
- Use **explicit waits** (via `BasePage.wait_for_element`) — zero `time.sleep()` calls
- Selector priority: `data-testid` > `id` > `name` > `role` > `aria-label` > stable CSS > fragile class chains
- Tests must be **isolated** — no shared mutable state between test methods
- Screenshot on failure is automatic (configured in `conftest.py`)

---

## MCP Tool Reference

| Tool | When to use |
|---|---|
| `probe_application_state(url)` | First action on any unfamiliar page |
| `inspect_current_dom(url, selector)` | Verify a specific selector before committing |
| `read_local_memory(query, category)` | Before writing any test or locator code |
| `write_local_memory(key, value, category, tags)` | After discovering a quirk or pattern |
| `record_selector_fix(page, element, old, new, reason)` | After fixing a broken selector |

---

## CLI Command Reference

| Command | Purpose |
|---|---|
| `framework generate-page --url <url>` | Scaffold POM class + Locator file |
| `framework generate-test --story <path>` | Generate pytest suite from story JSON |
| `framework run --suite <path>` | Execute tests with HTML report |
| `framework memory --action show` | Inspect stored memory |
| `framework memory --action search --query <q>` | Search memory |
