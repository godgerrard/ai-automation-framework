# AI Automation Framework — Copilot / Agent Instructions

These instructions apply to any AI assistant operating on this repository:
GitHub Copilot, Claude Code, Cursor, or any MCP-capable agent.

---

## Core Architecture Principle

**CLI = code generation. MCP = exploration. Never swap them.**

| Work type | Tool | Token cost |
|-----------|------|-----------|
| Generate locators, page objects, test files | CLI (`framework …`) | Zero |
| Run tests | CLI (`pytest`, `framework run`) | Zero |
| Parse plain-English stories | CLI (`framework add-story`) | Zero |
| Inspect live DOM to discover selectors | MCP (`inspect_current_dom`) | Tokens |
| Probe what interactive elements exist on a page | MCP (`probe_application_state`) | Tokens |
| Diagnose a failing selector | MCP (`inspect_current_dom`) | Tokens |
| Read / write application quirk notes | MCP (`read/write_local_memory`) | Tokens |

MCP tools cost tokens. CLI commands cost nothing. Use MCP only when you need
to look at the live application — typically only in the Corrector loop when
tests fail.

---

## Onboarding a New Application

When a user says they want to test an application, follow this conversation
sequence exactly. Do not skip steps or reorder them.

### Step 1 — Collect stories

Ask the user for their user stories or test requirements.
Accept any format: plain English, bullet points, numbered list, feature file, JSON.
Do NOT ask for anything else yet.

```
"Please share your user stories or test requirements — plain English is fine."
```

### Step 2 — Collect app URL

```
"What is the base URL of the application you want to test?"
```

### Step 3 — Collect credentials (if app has auth)

```
"Does your app require login? If so, what username and password should I use
 for testing? These will be saved in .env and never committed to git."
```

---

## Testing Scope — UI and API Only

This framework generates exactly two kinds of tests. Everything else is out of scope.

### In scope

| Kind | How |
|------|-----|
| **UI tests** | Playwright — navigation, clicks, form fills, assertions on visible text / element visibility / URL |
| **API tests** | Built-in HTTP client (`services/api_service.py` `APIService`) — REST calls, status codes, response bodies, headers, auth flows (Bearer / API key / Basic) |

### Out of scope — do NOT generate these

| Category | Reason |
|----------|---------|
| Direct database access (SQL, MongoDB, Redis, …) | No DB driver ships with this framework; database state is verified through the app's own UI or API |
| Raw network / socket / port / packet / DNS / TLS-handshake checks | Not application-behaviour testing |
| Infrastructure, load, performance, or security/penetration scanning | Use a dedicated tool (e.g. k6, OWASP ZAP) |
| Arbitrary shell or OS automation unrelated to exercising the app under test | Out of scope |

### Required agent behaviour when a request is out of scope

1. **Name the bottleneck plainly.** Example: "Checking that row directly in the database requires DB access — that is not a UI or API test, and this framework does not generate it."
2. **Offer the in-scope equivalent.** Example: "I can confirm the same outcome by asserting the result appears in the UI after the action, or by calling the relevant API endpoint and checking the response."
3. **Proceed with the in-scope version once the user agrees.**

After collecting requirements (Steps 1-3 below), if any requested item falls outside UI/API testing, briefly state the scope boundary and offer the equivalent before running setup.

Always reaffirm: the deliverable is runnable UI/API test files the user can re-run later.

---

### Step 4 — Run the setup wizard

Call the CLI once. Do not edit config.json or .env manually.

```bash
framework setup \
  --non-interactive \
  --url "<app-url>" \
  --name "<short-project-name>" \
  --username "<username>" \
  --password "<password>" \
  --browser chromium
```

This writes `.env` (credentials) and `config.json` (URL + browser).
No further config editing needed.

### Step 5 — Parse stories

For each story the user provided, call:

```bash
framework add-story --text "<story text>"
# or, if they gave you a file
framework add-story --file path/to/requirements.txt
```

This creates structured JSON files in `stories/`. Confirm how many stories
were created and what IDs they received before moving on.

### Step 6 — Build

```bash
framework build
```

This runs the full code-generation pipeline: it probes the live DOM headlessly,
maps story actions to real selectors, then writes locators + pages + tests.
No MCP needed here — the CLI handles DOM probing internally via Playwright.

### Step 7 — Enter the Loop

After build completes, enter the four-loop system described below.

---

## The Four-Loop System

Each loop has a clear purpose, a token budget, and hard stop conditions.
Run them in order. Never skip a loop.

```
Stories (plain English / JSON)
         │
         ▼  CLI — zero tokens
┌─────────────────────┐
│  LOOP 1: GENERATOR  │  framework build
│  story → code       │  Produces: locators, pages, tests
│  Max 3 cycles       │  Stop: all files generated, no syntax errors
└──────────┬──────────┘
           │
           ▼  CLI — zero tokens
┌─────────────────────┐
│  LOOP 2: TESTER     │  pytest → allure-results/
│  run → record       │  Produces: structured test results
│  1 run              │  Stop: pass → publish; fail → Corrector
└──────────┬──────────┘
           │ failures
           ▼  MCP — tokens spent ONLY here
┌─────────────────────┐
│  LOOP 3: CORRECTOR  │  inspect DOM → fix locator → re-run
│  diagnose → fix     │  1 MCP call per failing selector
│  Max 5 cycles       │  Stop rules from CLAUDE.md apply
└──────────┬──────────┘
           │ residual failures
           ▼  CLI — zero tokens
┌─────────────────────┐
│  LOOP 4: REPORTER   │  allure generate + bugs.md
│  classify → publish │  Selector bugs fixed; app bugs documented
└──────────┬──────────┘
           │
           ▼
   allure-report/index.html  +  bugs.md
```

---

### LOOP 1 — GENERATOR

**Purpose:** Turn story files into runnable test code.
**Tools:** CLI only. Zero tokens.
**Entry condition:** At least one `.json` file exists in `stories/`.

```bash
# Build all stories at once
framework build

# Or target one story
framework build --story stories/<story_id>.json
```

**Outputs created:**
- `locators/<name>_locators.py`
- `pages/<name>_page.py`
- `tests/workflows/test_<name>.py` (for UI stories)
- `tests/api/test_<name>_api.py` (for API stories)

**Stop conditions:**

| Condition | Action |
|-----------|--------|
| All story files have corresponding test files, no syntax errors | Stop — hand off to TESTER |
| Generated file has a `SyntaxError` | Retry `framework build` for that story (max 3 retries) |
| 3 retries exhausted on same story | Stop — report the story as unparseable; ask user to clarify |

Never edit generated files manually in this loop. If generation keeps failing,
the story text is ambiguous — ask the user to rephrase it.

---

### LOOP 2 — TESTER

**Purpose:** Run all generated tests and capture structured results.
**Tools:** CLI only. Zero tokens.
**Entry condition:** GENERATOR LOOP completed with at least one test file.

```bash
# Run suite, produce allure raw results
pytest tests/ \
  --alluredir=allure-results \
  --tb=short \
  --no-header \
  -q

# Generate the dashboard immediately after
allure generate allure-results --clean -o allure-report
```

**Outputs:**
- `allure-results/` — raw JSON per test (read by allure to build dashboard)
- `allure-report/` — HTML dashboard

**Stop conditions:**

| Condition | Action |
|-----------|--------|
| All tests pass | Stop — publish dashboard, report success to user |
| Some tests fail | Hand off to CORRECTOR LOOP with the exact list of failures |
| Zero tests collected | Stop — GENERATOR LOOP produced nothing runnable; escalate |

Parse pytest output to extract for each failure: test node ID, error message,
and the selector string if it appears in the traceback.

---

### LOOP 3 — CORRECTOR

**Purpose:** Diagnose and fix failing tests.
**Tools:** MCP for diagnosis. CLI for applying fixes.
**Token cost:** Tokens are spent here. One MCP call per failing selector — no more.
**Entry condition:** TESTER LOOP reported one or more failures.
**Max cycles:** 5

**For each failing test:**

**Step A — Classify the failure (see Bug Classification below).**

**Step B — If it is a selector bug** (element not found, timeout):

```
MCP call: inspect_current_dom(
  url="<app-url><page-path>",
  selector="button, input, [data-test], [aria-label]"
)
```

Read the response. Identify the real selector for the element.
Apply the fix via CLI:

```bash
framework fix-selector \
  --file locators/<name>_locators.py \
  --constant <CONSTANT_NAME> \
  --selector "<new-real-selector>"
```

Record the fix so it is not made again:

```
MCP call: record_selector_fix(
  page_name="<PageClass>",
  element_name="<CONSTANT_NAME>",
  original_selector="<broken>",
  fixed_selector="<working>",
  reason="<one sentence why it was wrong>"
)
```

**Step C — If it is an application bug** (selector worked, behaviour wrong):
Do NOT fix the test. Note it. It goes to REPORTER LOOP.

**Step D — After fixing selector bugs, re-run TESTER LOOP.**

**Stop conditions (from CLAUDE.md — non-negotiable):**

| Condition | Action |
|-----------|--------|
| All tests pass | Stop — publish dashboard |
| 5 cycles completed | Stop — report remaining failures; do not fix further |
| Same test fails the same way twice in a row | Stop — classify as application bug |
| A fix causes a previously passing test to fail | Stop — revert the fix; escalate to user |

Never weaken an assertion to reach green. If the assertion is correct and the
application does not match it, that is an application bug — document it, do not hide it.

---

### LOOP 4 — REPORTER

**Purpose:** Classify residual failures, write bug reports, publish dashboard.
**Tools:** CLI. Minimal tokens only for writing bug descriptions.
**Entry condition:** CORRECTOR LOOP has stopped (all green, or max cycles reached).

**Step 1 — Regenerate the dashboard with final results:**
```bash
pytest tests/ --alluredir=allure-results -q
allure generate allure-results --clean -o allure-report
```

**Step 2 — Write `bugs.md`:**

For every test classified as an application bug by the CORRECTOR LOOP:

```markdown
## BUG — <test_name>

**Severity:** Critical / High / Medium / Low
**Status:** Open
**Test:** `tests/workflows/test_<name>.py::<Class>::<method>`
**URL:** <app url + path where the bug occurs>
**Expected:** <what the test asserted>
**Actual:** <what the application returned>
**Selector:** <the locator that was confirmed working>

**Steps to reproduce:**
1. <derived from test steps>
2. …

**Evidence:** Screenshot in allure-report/
```

**Step 3 — Print the final summary:**

```
═══════════════════════════════════════════════════
  LOOP COMPLETE
═══════════════════════════════════════════════════
  Stories processed        : N
  Tests generated          : N
  Tests passed             : N  ✅
  Selector bugs fixed      : N
  Application bugs found   : N  🐛

  Dashboard  → allure-report/index.html
  Bug report → bugs.md
═══════════════════════════════════════════════════
```

This output is required. Never summarise without it.

---

## Bug Classification

This is the most important judgment in the CORRECTOR LOOP.

### Selector Bug — Fix it

The test logic is correct but the DOM element could not be found.

Symptoms:
- `TimeoutError: Waiting for locator("[data-test='login-btn']") to be visible`
- `ElementNotFoundError`
- `AssertionError: Expected 1 elements, found 0`

Action: Use MCP `inspect_current_dom` to find the real selector. Apply fix via CLI.
Do NOT change the assertion.

### Application Bug — Document it

The element was found but the application behaved incorrectly.

Symptoms:
- `AssertionError: Expected 'Dashboard', got 'Login'`
- `AssertionError: Expected HTTP 200, got 500`
- `AssertionError: 'Thank you for your order' not visible after completing checkout`
- Any assertion failure where the locator did NOT time out

Action: Do NOT change the test. Write an entry in `bugs.md`.
Mark the Allure test result with the label `BUG`.

### Test Logic Bug — Regenerate

The test was generated with an incorrect assumption about the app's structure
(wrong URL path, wrong expected text, wrong form field target).

Symptoms:
- `AssertionError: Expected URL to contain '/dashboard', got '/home'`
- URL path in the story does not exist on the real app

Action: Use MCP `probe_application_state` to discover the real structure.
Update the relevant story JSON file, then re-run GENERATOR LOOP for that story only.

---

## CLI Command Reference

All zero-token operations. Run these directly.

```bash
# Interactive setup wizard — collects URL, credentials, writes .env + config.json
framework setup

# Parse a plain-English story → creates stories/<id>.json
framework add-story --text "As a user I want to log in to the admin panel..."
framework add-story --file my_requirements.txt

# Run full code-generation pipeline for all stories
framework build

# Build one story only
framework build --story stories/myapp_login_001.json

# Fix a single locator constant (used by CORRECTOR LOOP)
framework fix-selector \
  --file locators/myapp_locators.py \
  --constant LOGIN_BUTTON \
  --selector "[data-test='login-btn']"

# Run tests (all standard pytest flags work)
pytest tests/
pytest tests/ -m smoke
pytest tests/ -m "smoke and api"
pytest tests/ -m "not regression"
pytest tests/ --alluredir=allure-results -q

# Run via CLI wrapper (auto-applies browser + report config)
framework run --suite tests/ --headless

# Inspect and manage the self-healing memory
framework memory --action show
framework memory --action search --query "login"
framework memory --action clear
```

---

## MCP Tool Reference

Call these only when you need to look at the live running application.
Each call costs tokens. Be targeted — one call per problem.

```python
# FIRST action on any unfamiliar page — returns all interactive elements
probe_application_state(url="https://app.com/login", depth=2)
# Returns: inputs, buttons, links, forms, headings, aria roles

# Diagnose a specific failing selector — scope it tightly
inspect_current_dom(url="https://app.com/login", selector="button, [data-test]")
# Returns: tag, text, attributes, visibility, bounding box for each match

# Check for known quirks before generating code for a page
read_local_memory(query="login")
# Returns: previously recorded selector fixes and quirks for this area

# Record a corrected selector (prevents the same mistake next run)
record_selector_fix(
    page_name="LoginPage",
    element_name="LOGIN_BUTTON",
    original_selector="button.login",
    fixed_selector="[data-test='login-button']",
    reason="CSS class removed in v2.3 frontend refactor"
)

# Store an application-specific note for future reference
write_local_memory(
    key="checkout.postal_validation",
    value="Field silently rejects non-numeric input — no error shown to user",
    category="quirk",
    tags=["checkout", "validation"]
)
```

---

## Selector Priority Rules

When `framework build` or the CORRECTOR LOOP maps an action to a DOM element,
apply this priority. Never choose a lower priority if a higher one exists.

```
1. [data-test='…']       purpose-built for testing; survives styling changes
2. [data-testid='…']     common alternative to data-test
3. #id                   stable when maintained
4. [aria-label='…']      accessible and readable
5. [name='…']            reliable for form fields
6. button:has-text('…')  Playwright text selector; readable but brittle on i18n apps
7. .specific-class       only if unique and unlikely to change
8. //xpath               absolute last resort
```

Never use positional selectors (`.item:nth-child(3)`) in test code.

---

## Allure Integration

Install once (if not already installed):

```bash
pip install allure-pytest

# Allure CLI — needed to generate the dashboard
# Windows:  scoop install allure
# macOS:    brew install allure
# Linux:    sudo apt-get install allure
```

Add story-level labels to generated tests when the story has feature/severity metadata:

```python
import allure

@allure.feature("Authentication")
@allure.story("Standard user login")
@allure.severity(allure.severity_level.CRITICAL)
def test_valid_login(self, page, memory):
    ...
```

Generate and open dashboard:

```bash
allure generate allure-results --clean -o allure-report
allure open allure-report
```

In CI, upload the `allure-report/` directory as a pipeline artifact so
stakeholders can view results without local setup.

---

## Project File Rules

| Path pattern | Git status | Rule |
|---|---|---|
| `core/**`, `services/**`, `cli/**` | Tracked | Never edit — framework engine |
| `mcp_server/**`, `utils/**` | Tracked | Never edit — framework engine |
| `tests/conftest.py`, `config.py` | Tracked | Never edit — framework fixtures |
| `stories/templates/**` | Tracked | Read-only reference |
| `locators/*.py` | **Gitignored** | Generated per project |
| `pages/*.py` | **Gitignored** | Generated per project |
| `tests/workflows/test_*.py` | **Gitignored** | Generated per project |
| `tests/api/test_*.py` | **Gitignored** | Generated per project |
| `stories/*.json` | **Gitignored** | Generated per project |
| `allure-results/`, `allure-report/` | **Gitignored** | Runtime output |
| `bugs.md` | **Gitignored** | Runtime output |
| `memory/` | **Gitignored** | Self-healing runtime data |

Generated project files are gitignored so the framework repo stays
application-agnostic and can be used for any client.

---

## Loop Stop Rules (Non-Negotiable)

Defined in `CLAUDE.md`. The CORRECTOR LOOP enforces all four.

| Rule | Condition | Action |
|------|-----------|--------|
| All green | Every test passes | Stop — publish dashboard — report success WITH pytest output |
| 5 cycles | Max CORRECTOR cycles reached | Stop — report what still fails and what was tried |
| Same failure twice | Identical failure on consecutive cycles | Stop — classify as application bug |
| Regression | A fix causes a passing test to fail | Stop — revert — escalate to user |

**Never** report success without actual pytest output from the final run.
**Never** delete or weaken an assertion to clear a failure. Fix the code or file the bug.

---

## Token Budget Guidelines

| Activity | Approximate tokens | Notes |
|---|---|---|
| `framework build` (full pipeline) | 0 | Pure CLI |
| `pytest` run | 0 | Pure CLI |
| `probe_application_state` (one page) | 800–1500 | Call once per page; reuse the result |
| `inspect_current_dom` (one selector) | 300–600 | Scope with a tight CSS selector |
| Classifying one bug | 100–200 | Read error → write one sentence |
| Full CORRECTOR LOOP (20-test suite, 5 failing) | ~3000–5000 | One MCP call per failing selector |

Keep MCP usage surgical. A well-scoped `inspect_current_dom` call with
`selector="button, input, [data-test]"` is far cheaper and more useful than
`selector="body"` which dumps the entire DOM.
