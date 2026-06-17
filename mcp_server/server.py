"""
FastMCP Server — exposes framework tools to IDE AI agents (Claude Code, Copilot, etc.).

Start modes:
  Stdio (default for IDE integration):
      python mcp_server/server.py

  HTTP (for remote/multi-client):
      fastmcp run mcp_server/server.py --transport streamable-http --port 8765

Claude Code integration (.claude/mcp.json):
  {
    "mcpServers": {
      "ai-automation": {
        "command": "python",
        "args": ["mcp_server/server.py"],
        "cwd": "<path-to-repo>"
      }
    }
  }
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when this file is executed directly
# (i.e. `python mcp_server/server.py`). Not needed after `pip install -e .`.
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP

from mcp_server.tools import ApplicationProber, DOMInspector, MemoryTool

mcp = FastMCP(
    name="AI Automation Framework",
    instructions=(
        "You are connected to the AI Automation Framework MCP server.\n\n"
        "TRIAGE RULES:\n"
        "1. Before writing ANY test or locator code, call read_local_memory to check for known quirks.\n"
        "2. Use probe_application_state as your first step when exploring an unfamiliar page.\n"
        "3. Use inspect_current_dom to verify specific selectors before committing them to code.\n"
        "4. After fixing a broken selector, call record_selector_fix so future generation is self-healing.\n"
        "5. Never write POM classes or test scripts from scratch — invoke the Framework CLI instead."
    ),
)

_inspector = DOMInspector()
_prober = ApplicationProber()
_memory = MemoryTool()


# ── Tool: inspect_current_dom ─────────────────────────────────────────────────

@mcp.tool()
async def inspect_current_dom(url: str, selector: str = "body") -> dict:
    """
    Analyzes the live DOM at *url* for elements matching *selector*.

    Returns each matched element's tag, text, attributes, child count,
    visibility flag, and bounding box. Limits output to 25 elements.

    Use this to discover exact attribute values for locators before writing
    or updating a Locator class.

    Args:
        url:      Full URL of the page to inspect (must include http/https).
        selector: CSS selector to scope the inspection (default: "body").
    """
    return await _inspector.inspect(url, selector)


# ── Tool: probe_application_state ─────────────────────────────────────────────

@mcp.tool()
async def probe_application_state(url: str, depth: int = 2) -> dict:
    """
    Deep-scans the application page at *url* and returns:
      - All interactive elements (buttons, inputs, links, roles)
      - All form definitions with field metadata
      - Navigation links
      - Page metadata (title, headings, meta description)

    Use this as your *first action* when exploring any unfamiliar page.

    Args:
        url:   Full URL to probe.
        depth: Exploration depth hint (1-3).
    """
    return await _prober.probe(url, depth)


# ── Tool: read_local_memory ───────────────────────────────────────────────────

@mcp.tool()
def read_local_memory(query: str = "", category: str = "") -> dict:
    """
    Queries the persistent local memory engine for application-specific context.

    Provide *query* for free-text search across keys, values, and tags.
    Provide *category* to filter by type: selector | quirk | workflow | failure | general.
    Omit both to retrieve all stored entries.

    ALWAYS call this before writing test code for a page.

    Args:
        query:    Free-text search string.
        category: Category filter (optional).
    """
    return _memory.read(query, category)


# ── Tool: write_local_memory ──────────────────────────────────────────────────

@mcp.tool()
def write_local_memory(
    key: str,
    value: str,
    category: str = "general",
    tags: list[str] | None = None,
) -> dict:
    """
    Persists a knowledge entry to the local memory engine.

    Use this whenever you discover application quirks, selector patterns,
    or behavioral notes that should inform future code generation.

    Args:
        key:      Descriptive identifier, e.g. "login_page.submit_button_pattern"
        value:    The knowledge to store.
        category: One of: selector | quirk | workflow | failure | general
        tags:     List of searchable tags (optional).
    """
    return _memory.write(key, value, category, tags)


# ── Tool: record_selector_fix ─────────────────────────────────────────────────

@mcp.tool()
def record_selector_fix(
    page_name: str,
    element_name: str,
    original_selector: str,
    fixed_selector: str,
    reason: str,
) -> dict:
    """
    Records a corrected element selector to enable self-healing test generation.

    Call this every time you change a selector from what was auto-generated.
    Future CLI runs will consult this memory to avoid producing the same
    broken selector again.

    Args:
        page_name:          Python class name of the page (e.g. "LoginPage").
        element_name:       Attribute name in the Locator class (e.g. "SUBMIT_BUTTON").
        original_selector:  The selector that failed.
        fixed_selector:     The working replacement.
        reason:             Why the original was wrong.
    """
    return _memory.record_fix(page_name, element_name, original_selector, fixed_selector, reason)


if __name__ == "__main__":
    mcp.run()
