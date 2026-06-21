# AI Automation Framework — Contribution Guidelines

## What this repo IS

A reusable, client-agnostic test automation framework built on Playwright + pytest.
It ships the **engine** — page base classes, API client, memory engine, MCP server,
CLI, and code generators. It does NOT ship test suites for any specific application.

## What belongs in git (framework code)

```
core/           base classes (BasePage, APIBase, MemoryEngine, DriverFactory)
services/       HTTP client (APIService, APIResponse)
cli/            CLI commands (framework init-project, generate-page, generate-test, run …)
utils/          Helpers, CodeGenerator, APICodeGenerator, ProjectScaffolder
mcp_server/     MCP FastMCP server and tool definitions
tests/conftest.py  Framework-level pytest fixtures only
config.py       Configuration loader
pyproject.toml  Build / dependency manifest
stories/templates/  Reference story templates (READ-ONLY reference)
```

## What does NOT belong in git (project-specific)

These files are generated per target application and are listed in `.gitignore`.
**Never commit them to the framework repo.** Each client keeps their own fork or
separate directory with their project files.

| Directory / Pattern         | Contents                                    |
|-----------------------------|---------------------------------------------|
| `locators/*.py`             | Selectors for a specific application's DOM  |
| `pages/*.py`                | Page Objects for a specific application     |
| `tests/workflows/test_*.py` | UI test suites for a specific application   |
| `tests/api/test_*.py`       | API test suites for a specific application  |
| `stories/*.json`            | User stories for a specific application     |
| `memory/framework_memory.json` | Runtime self-healing data               |
| `reports/`                  | Test run output (HTML, screenshots, videos) |

## Starting a new project

```bash
# Scaffold skeleton files for a web application
framework init-project --url https://yourapp.com --name yourapp

# Scaffold for an API-only project
framework init-project --url https://api.yourapp.com --name yourapp --type api

# Scaffold both web and API skeletons
framework init-project --url https://yourapp.com --name yourapp --type both
```

Then:
1. Update selectors in `locators/yourapp_locators.py` (use the MCP DOM inspector)
2. Extend page methods in `pages/yourapp_page.py`
3. Fill in test assertions in `tests/workflows/test_yourapp.py`
4. Run: `framework run --suite tests/ --base-url https://yourapp.com`

## Agent loop stop rules

The Builder+Checker agent loop stops when:
- All checks are green
- 5 cycles are exhausted
- The same failure appears twice in a row (loop is not converging)
- A fix breaks a previously passing check

Never report success without showing checker output.
Never weaken or delete an assertion to make a test pass — fix the code or the locator.

## Code style

- Page Objects go in `pages/`, inherit from `BasePage`
- Locators go in `locators/`, pure string constants (no logic)
- Tests use pytest classes; `memory` fixture is always a parameter for failure tracking
- `data-test` attributes preferred over `id`/class; never use XPath unless unavoidable
- API tests use `APIResponse` fluent assertions — never `assert resp.status_code == 200` directly
