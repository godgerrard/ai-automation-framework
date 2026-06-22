"""
Tests for mcp_server.tools: DOMInspector, ApplicationProber, MemoryTool.
Uses asyncio.run() to drive coroutines (no pytest-asyncio needed).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure repo root on path
_root = Path(__file__).parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.memory_engine import MemoryEngine
from mcp_server.tools import ApplicationProber, DOMInspector, MemoryTool


# ── Async context manager mock for async_playwright ──────────────────────────

def _make_playwright_mock(elements=None, title="Test Page"):
    """Build a fully mocked async_playwright context manager."""
    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.goto = AsyncMock()
    mock_page.title = AsyncMock(return_value=title)
    mock_page.evaluate = AsyncMock(return_value=elements or [])

    # locator mock
    mock_locator = AsyncMock()
    mock_locator.count = AsyncMock(return_value=1)
    mock_locator.nth = MagicMock(return_value=mock_locator)
    mock_locator.inner_text = AsyncMock(return_value="sample text")
    mock_locator.evaluate = AsyncMock(return_value="div")
    mock_locator.bounding_box = AsyncMock(return_value={"x": 0, "y": 0, "width": 100, "height": 50})
    mock_page.locator = MagicMock(return_value=mock_locator)

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = AsyncMock()
    mock_pw.chromium = mock_chromium

    # async context manager: __aenter__ returns mock_pw, __aexit__ is a no-op
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    return mock_ctx, mock_page


# ── DOMInspector ─────────────────────────────────────────────────────────────

def test_dom_inspector_inspect_returns_ok():
    mock_ctx, mock_page = _make_playwright_mock()

    with patch("mcp_server.tools.async_playwright", return_value=mock_ctx):
        inspector = DOMInspector()
        result = asyncio.run(inspector.inspect("https://example.com", "body"))

    assert result["status"] == "ok"
    assert "elements" in result
    assert "url" in result


def test_dom_inspector_inspect_contains_total_matches():
    mock_ctx, mock_page = _make_playwright_mock()

    with patch("mcp_server.tools.async_playwright", return_value=mock_ctx):
        inspector = DOMInspector()
        result = asyncio.run(inspector.inspect("https://example.com"))

    assert "total_matches" in result


def test_dom_inspector_inspect_returns_page_title():
    mock_ctx, mock_page = _make_playwright_mock(title="My App")

    with patch("mcp_server.tools.async_playwright", return_value=mock_ctx):
        inspector = DOMInspector()
        result = asyncio.run(inspector.inspect("https://example.com"))

    assert result.get("page_title") == "My App"


# ── ApplicationProber ─────────────────────────────────────────────────────────

def test_application_prober_probe_returns_ok():
    interactive = [
        {"tag": "button", "type": "submit", "id": "login-btn", "name": None,
         "class": "", "text": "Login", "placeholder": None, "href": None,
         "role": None, "ariaLabel": None, "dataTestId": None, "visible": True}
    ]

    mock_ctx, mock_page = _make_playwright_mock(elements=interactive)
    # ApplicationProber calls evaluate multiple times (interactive, forms, nav, meta)
    meta_result = {"title": "App", "description": None, "h1": [], "h2": []}

    call_count = {"n": 0}
    eval_returns = [interactive, [], [], meta_result]

    async def multi_evaluate(js):
        idx = call_count["n"]
        call_count["n"] += 1
        if idx < len(eval_returns):
            return eval_returns[idx]
        return []

    mock_page.evaluate = multi_evaluate

    with patch("mcp_server.tools.async_playwright", return_value=mock_ctx):
        prober = ApplicationProber()
        result = asyncio.run(prober.probe("https://example.com"))

    assert result["status"] == "ok"
    assert "interactive_elements" in result


def test_application_prober_probe_has_summary():
    mock_ctx, mock_page = _make_playwright_mock()

    call_count = {"n": 0}
    meta_result = {"title": "App", "description": None, "h1": [], "h2": []}
    eval_returns = [[], [], [], meta_result]

    async def multi_evaluate(js):
        idx = call_count["n"]
        call_count["n"] += 1
        if idx < len(eval_returns):
            return eval_returns[idx]
        return []

    mock_page.evaluate = multi_evaluate

    with patch("mcp_server.tools.async_playwright", return_value=mock_ctx):
        prober = ApplicationProber()
        result = asyncio.run(prober.probe("https://example.com"))

    assert "summary" in result


# ── MemoryTool ────────────────────────────────────────────────────────────────

@pytest.fixture
def mem_engine(tmp_path):
    db = tmp_path / "mem" / "test.json"
    return MemoryEngine(str(db))


def test_memory_tool_write_delegates_to_engine(mem_engine):
    tool = MemoryTool()
    tool._mem = mem_engine

    result = tool.write("test_key", "test_value", category="general")
    assert result["status"] == "ok"
    assert "id" in result
    assert result["key"] == "test_key"


def test_memory_tool_read_returns_all_when_no_query(mem_engine):
    tool = MemoryTool()
    tool._mem = mem_engine
    mem_engine.remember("k1", "v1")
    mem_engine.remember("k2", "v2")

    result = tool.read()
    assert result["count"] >= 2
    assert "entries" in result


def test_memory_tool_read_by_query(mem_engine):
    tool = MemoryTool()
    tool._mem = mem_engine
    mem_engine.remember("login_key", "login_value")

    result = tool.read(query="login_key")
    assert result["count"] >= 1
    assert any(e["key"] == "login_key" for e in result["entries"])


def test_memory_tool_read_by_category(mem_engine):
    tool = MemoryTool()
    tool._mem = mem_engine
    mem_engine.remember("sel1", "#btn", category="selector")
    mem_engine.remember("wf1", "navigate", category="workflow")

    result = tool.read(category="selector")
    assert result["count"] >= 1
    assert all(e["category"] == "selector" for e in result["entries"])


def test_memory_tool_record_fix(mem_engine):
    tool = MemoryTool()
    tool._mem = mem_engine

    result = tool.record_fix("login_page", "LOGIN_BTN", "#old", "#new", "corrector fix")
    assert result["status"] == "ok"
    assert "id" in result
    assert "login_page" in result["message"]

    # Verify stored in selector category
    sels = mem_engine.recall_by_category("selector")
    assert len(sels) >= 1
    assert sels[0]["value"]["original_selector"] == "#old"
    assert sels[0]["value"]["fixed_selector"] == "#new"
