"""
Pytest configuration: fixtures, CLI options, and failure hooks.

Design notes:
  - pytest-playwright is NOT used as a plugin; manual fixtures give us full
    control over scoping, viewport, and memory integration without option conflicts.
  - browser is session-scoped (expensive); context and page are function-scoped
    (ensures test isolation — no shared DOM state between tests).
  - The failure hook uses wrapper=True (pytest 8.1+ style) to avoid the
    deprecated hookwrapper pattern.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

# Defensive sys.path — ensures imports work both when installed via
# `pip install -e .` and when pytest is run directly from repo root.
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from config import load_config
from core.memory_engine import MemoryEngine
from services.api_service import APIService

CONFIG = load_config()


# ── CLI options ───────────────────────────────────────────────────────────────

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--browser-type",
        default=CONFIG.browser.browser,
        choices=["chromium", "firefox", "webkit"],
        help="Playwright browser to use.",
    )
    parser.addoption(
        "--headed",
        action="store_true",
        default=not CONFIG.browser.headless,
        help="Run browser in headed (visible) mode.",
    )
    parser.addoption(
        "--app-url",
        default=CONFIG.app.base_url,
        help="Override the application base URL.",
    )
    parser.addoption(
        "--slow-mo",
        type=int,
        default=CONFIG.browser.slow_mo,
        help="Slow down Playwright actions by N milliseconds.",
    )
    parser.addoption(
        "--api-url",
        default=CONFIG.app.base_url,
        help="Base URL for API test suites. Defaults to --app-url value.",
    )


# ── Session-scoped fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--app-url")


@pytest.fixture(scope="session")
def memory() -> MemoryEngine:
    """Shared memory engine for the entire test session."""
    return MemoryEngine(CONFIG.memory_db_path)


@pytest.fixture(scope="session")
def api(base_url: str) -> APIService:
    """API client for web-test setup/teardown. Retries transient errors."""
    return APIService(base_url, max_retries=2)


@pytest.fixture(scope="session")
def api_client(request: pytest.FixtureRequest) -> APIService:
    """Standalone API client for API test suites. No retries — tests see raw status codes."""
    url = request.config.getoption("--api-url")
    return APIService(url, max_retries=0)


@pytest.fixture(scope="session")
def _playwright():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(request: pytest.FixtureRequest, _playwright) -> Generator[Browser, None, None]:
    browser_type = request.config.getoption("--browser-type")
    headed = request.config.getoption("--headed")
    slow_mo = request.config.getoption("--slow-mo")

    launcher = getattr(_playwright, browser_type)
    b = launcher.launch(headless=not headed, slow_mo=slow_mo)
    yield b
    b.close()


# ── Function-scoped fixtures (fresh per test) ─────────────────────────────────

@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    ctx = browser.new_context(
        viewport=CONFIG.browser.viewport,
        ignore_https_errors=True,
    )
    yield ctx
    ctx.close()


@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    p = context.new_page()
    p.set_default_timeout(CONFIG.browser.timeout)
    yield p
    p.close()


# ── Failure hook (pytest 8.1+ wrapper style) ──────────────────────────────────

@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    report = yield  # passes control to inner hooks; returns TestReport

    if report.when != "call" or not report.failed:
        return report

    # Auto-screenshot on failure
    page_obj: Page | None = item.funcargs.get("page")
    if page_obj and CONFIG.app.screenshot_on_failure:
        screenshots_dir = Path(CONFIG.reports_dir) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        safe_name = item.nodeid.replace("/", "_").replace("::", "__").replace(" ", "-")
        shot_path = screenshots_dir / f"{safe_name}.png"
        try:
            page_obj.screenshot(path=str(shot_path), full_page=True)
        except Exception:
            pass  # never let the hook itself fail the test run

    # Persist failure to memory engine for self-healing
    mem: MemoryEngine | None = item.funcargs.get("memory")
    if mem:
        is_api_test = item.funcargs.get("page") is None
        mem.record_failure(
            test_name=item.nodeid,
            selector="N/A (API test)" if is_api_test else "unknown",
            error=str(report.longrepr)[:500],
        )

    return report
