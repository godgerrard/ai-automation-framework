# AI Automation Framework — GitHub Copilot Agent Instructions

These instructions govern Copilot's behaviour when working inside this repository.
Copilot executes each step inline using terminal commands and MCP tool calls.
There are no sub-agents. Every action happens in the current conversation.

---

## Core Rule: CLI vs MCP

| Task | Tool | Token cost |
|------|------|-----------|
| Setup, story parsing, code generation, test execution, selector patching | CLI (`framework …`) | Zero |
| Inspect live DOM to find real selectors | MCP `inspect_current_dom` | ~400 |
| Probe all interactive elements on a page | MCP `probe_application_state` | ~1200 |
| Read/write self-healing memory | MCP `read_local_memory` / `write_local_memory` | ~100 |

Never call an MCP tool where a CLI command can do the job.

---

## Onboarding — Collect Three Inputs First

When the user asks to test an application, collect in this order:

**Step 1 — Stories**
```
"Share your test requirements — plain English, bullet points, or Gherkin."
```

**Step 2 — Base URL**
```
"What is the base URL of the application?"
```

**Step 3 — Credentials**
```
"Does the app need login? If yes, share username and password.
 They will be saved in .env (gitignored — never committed)."
```

After collecting all three inputs, if any requested item falls outside UI/API testing,
state the scope boundary (see below) and offer the equivalent before running setup.

---

## Testing Scope -- UI and API Only

This framework generates exactly two kinds of tests:

**In scope:**
- UI tests via Playwright: navigation, clicks, form fills, assertions on visible text /
  element visibility / URL.
- API tests via the built-in HTTP client (services/api_service.py APIService): REST calls,
  status codes, response bodies, headers, and auth flows.

**Out of scope -- do NOT generate these:**
- Direct database access (SQL, MongoDB, Redis, etc.) -- no DB driver ships with this
  framework; verify state through the app's own UI or API instead.
- Raw network / socket / port / DNS / TLS-handshake checks -- not application-behaviour
  testing.
- Infrastructure, load, performance, or security/penetration scanning -- use a dedicated
  tool (e.g. k6, OWASP ZAP).
- Arbitrary shell or OS automation unrelated to exercising the app.

**When a request is out of scope:**
1. Name the bottleneck plainly: "Checking that row directly in the database requires DB
   access -- that is not a UI or API test, and this framework does not generate it."
2. Offer the in-scope equivalent: "I can assert the same outcome through the UI after
   the action, or by calling the relevant API endpoint and checking the response."
3. Proceed with the in-scope version once the user agrees.

The deliverable is always runnable UI/API test files the user can re-run later.

---

## Setup -> Build -> Loop

Run these commands in sequence. Never skip a step.

### Step 4 — Setup wizard
```bash
framework setup --non-interactive \
  --url "<base-url>" \
  --name "<project-name>" \
  --username "<username>" \
  --password "<password>" \
  --browser chromium
```

### Step 5 — Parse stories
```bash
framework add-story --text "<story text>"
# or from file:
framework add-story --file requirements.txt
```
Confirm how many stories were created and what IDs they received.

### Step 6 — Build (probe DOM + generate code)
```bash
framework build
```
Outputs:
- `locators/<name>_locators.py`
- `pages/<name>_page.py`
- `tests/workflows/test_<id>.py`

---

## Four-Loop Pipeline — Execute Each Loop Inline

### LOOP 1 — GENERATOR
All story files must produce test files with zero syntax errors.

```bash
# Syntax-check every generated test
python -m py_compile tests/workflows/test_*.py
python -m py_compile locators/*.py
python -m py_compile pages/*.py
```

If SyntaxError → re-run `framework build` for that story (max 3 retries).
If 3 retries fail → story text is ambiguous. Ask user to rephrase, then rebuild.
Never edit generated files manually.

---

### LOOP 2 — TESTER
Run all tests and record results.

```bash
pytest tests/ --alluredir=allure-results --tb=short --no-header -q
```

Parse the output:
- All pass → skip LOOP 3, go straight to LOOP 4
- Some fail → collect each failing test's: node ID, error type, selector string if present
- Zero collected → GENERATOR produced nothing runnable; escalate to user

---

### LOOP 3 — CORRECTOR (max 5 cycles, non-negotiable)

For each failing test, classify then act:

#### Classification

| Error type | Classification | Action |
|---|---|---|
| `TimeoutError`, `ElementNotFoundError`, `found 0` | Selector bug | Fix it (see below) |
| `AssertionError` where element WAS found | Application bug | Document it |
| Wrong URL path in assertion | Test logic bug | Probe + regenerate |

#### Fix a selector bug

```
# 1. Inspect the live DOM (one call per failing selector)
inspect_current_dom(
  url="<base_url><page_path>",
  selector="button, input, [data-test], [data-testid], [aria-label], a, select"
)
```

Find the correct element in the response. Then:

```bash
# 2. Patch the selector
framework fix-selector \
  --file locators/<name>_locators.py \
  --constant <CONSTANT_NAME> \
  --selector "<real-selector>"
```

```
# 3. Record the fix to prevent recurrence
record_selector_fix(
  page_name="<PageClass>",
  element_name="<CONSTANT_NAME>",
  original_selector="<broken-value>",
  fixed_selector="<working-value>",
  reason="<one sentence>"
)
```

```bash
# 4. Re-run after fixing all selectors in this cycle
pytest tests/ --alluredir=allure-results --tb=short -q
```

#### Document an application bug
Do NOT change the test. Note exactly:
```
BUG: <test_node_id>
URL: <where it fails>
Expected: <assertion>
Actual: <what app returned>
Selector: <confirmed working>
```

#### Hard stop rules — check after every cycle

| Condition | Action |
|---|---|
| All tests pass | Stop — go to LOOP 4 |
| 5 cycles completed | Stop — report remaining failures — go to LOOP 4 |
| Same test fails the same way twice | Stop — classify as application bug — go to LOOP 4 |
| A fix causes a previously passing test to fail | STOP EVERYTHING — revert the fix — escalate to user |

**Never** report success without showing actual pytest output.
**Never** weaken an assertion. Fix the locator or file the bug.

---

### LOOP 4 — REPORTER (always runs, even if failures remain)

**Step 1 — Regenerate report**
```bash
pytest tests/ --alluredir=allure-results -q
allure generate allure-results --clean -o allure-report
```
If `allure` CLI is not installed, `framework run --headless` generates a fallback HTML report.

**Step 2 — Write bugs.md** for every application bug from LOOP 3:
```markdown
# Bug Report

## BUG-001 — <test name>
**Severity:** Critical / High / Medium / Low
**Status:** Open
**Test:** `<full::node::id>`
**URL:** <app URL where it fails>
**Expected:** <assertion description>
**Actual:** <what the application returned>
**Confirmed selector:** <working locator>

**Steps to reproduce:**
1. Navigate to <url>
2. <derived from test steps>
```

**Step 3 — Print final summary (required — never omit)**
```
═══════════════════════════════════════════════════════
  AI AUTOMATION FRAMEWORK — RUN COMPLETE
═══════════════════════════════════════════════════════
  Date              : <ISO date>
  Application       : <base url>
  Stories processed : N
  Tests generated   : N

  Results
  ───────
  Passed            : N
  Selector bugs     : N  (fixed automatically)
  Application bugs  : N  (see bugs.md)
  Still failing     : N  (corrector max cycles reached)

  Outputs
  ───────
  Dashboard         → allure-report/index.html
  Bug report        → bugs.md
═══════════════════════════════════════════════════════
```

---

## MCP Tool Reference

Call these only when you need to look at the live app. One call per problem.

```python
# Map all interactive elements on a page — use FIRST on any unfamiliar page
probe_application_state(url="https://app.com/login", depth=2)

# Diagnose a specific failing selector — scope it tightly
inspect_current_dom(url="https://app.com/login", selector="button, input, [data-test]")

# Check memory before generating for a page
read_local_memory(query="login")

# Record a confirmed fix
record_selector_fix(
  page_name="LoginPage",
  element_name="SUBMIT_BUTTON",
  original_selector="button.submit",
  fixed_selector="[data-test='login-button']",
  reason="CSS class removed in v2 refactor"
)

# Store a quirk note
write_local_memory(
  key="checkout.address_validation",
  value="Postal code field rejects non-numeric silently",
  category="quirk",
  tags=["checkout", "validation"]
)
```

---

## Selector Priority (highest → lowest)
1. `[data-test='…']`
2. `[data-testid='…']`
3. `#id`
4. `[aria-label='…']`
5. `[name='…']`
6. `button:has-text('…')`
7. `.class-name`
8. XPath (last resort)

Never use positional selectors (`:nth-child(3)`).

---

## CLI Quick Reference
```bash
framework setup           # wizard: URL + credentials + browser
framework add-story       # plain English → stories/*.json
framework build           # DOM probe + code generation
framework run --headless  # pytest + Allure report
framework fix-selector    # patch one broken locator
framework memory --action show    # inspect memory store
framework memory --action clear   # wipe memory
framework clean                   # wipe all run artifacts before a fresh run
```

---

## File Ownership

| Path | Status | Rule |
|---|---|---|
| `core/`, `services/`, `cli/`, `utils/`, `mcp_server/` | Tracked (engine) | Never edit |
| `tests/conftest.py`, `config.py` | Tracked | Never edit |
| `locators/*.py`, `pages/*.py`, `tests/workflows/test_*.py` | Gitignored | Generated per project |
| `stories/*.json`, `allure-results/`, `allure-report/`, `bugs.md` | Gitignored | Runtime output |
| `.env` | Gitignored | Credentials — never commit |

---

## Memory System — When It Helps and When It Doesn't

**Helps:**
- Second+ run against the same project — past selector fixes are applied automatically
- Agent consults `read_local_memory` before generating code for a known page
- `record_selector_fix` prevents the same broken selector being generated again

**Does not help:**
- First run on a new project (memory is empty on fresh clone)
- If you change the project name in `framework setup` (memory keys won't match)
- If `framework clean` or `framework memory --action clear` was run (memory wiped)
- If the agent forgets to call `read_local_memory` before generating — MCP must be called explicitly

**Bottom line:** memory compounds value across repeated runs on the same project.
On a first-run POC demo, expect zero memory benefit — that's by design.
