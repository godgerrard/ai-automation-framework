"""
Tests for BasePage with a MagicMock Page.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from core.base_page import BasePage


@pytest.fixture
def mock_page():
    page = MagicMock()
    # Set up .url and .title() defaults
    page.url = "https://example.com/dashboard"
    page.title.return_value = "Dashboard"
    return page


@pytest.fixture
def bp(mock_page):
    return BasePage(mock_page, "https://example.com")


# ── navigate ──────────────────────────────────────────────────────────────────

def test_navigate_with_path(bp, mock_page):
    bp.navigate("/login")
    mock_page.goto.assert_called_once_with("https://example.com/login", wait_until="networkidle")


def test_navigate_no_path(bp, mock_page):
    bp.navigate()
    mock_page.goto.assert_called_once_with("https://example.com", wait_until="networkidle")


def test_navigate_empty_path(bp, mock_page):
    bp.navigate("")
    mock_page.goto.assert_called_once_with("https://example.com", wait_until="networkidle")


# ── base_url strips trailing slash ────────────────────────────────────────────

def test_base_url_strips_trailing_slash(mock_page):
    bp = BasePage(mock_page, "https://example.com/")
    assert bp.base_url == "https://example.com"


def test_base_url_no_slash_unchanged(mock_page):
    bp = BasePage(mock_page, "https://example.com")
    assert bp.base_url == "https://example.com"


# ── fill calls clear then fill ────────────────────────────────────────────────

def test_fill_calls_clear_then_fill(bp, mock_page):
    mock_locator = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_locator.wait_for.return_value = None

    # wait_for_element returns the locator
    bp.fill("#input", "hello")

    mock_locator.clear.assert_called_once()
    mock_locator.fill.assert_called_once_with("hello")


# ── is_visible returns False on PlaywrightTimeout ────────────────────────────

def test_is_visible_returns_true_when_visible(bp, mock_page):
    mock_locator = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_locator.wait_for.return_value = None

    result = bp.is_visible("#element")
    assert result is True


def test_is_visible_returns_false_on_timeout(bp, mock_page):
    mock_locator = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_locator.wait_for.side_effect = PlaywrightTimeout("timeout")

    result = bp.is_visible("#missing-element")
    assert result is False


# ── current_url / page_title delegate ────────────────────────────────────────

def test_current_url_delegates(bp, mock_page):
    mock_page.url = "https://example.com/page"
    assert bp.current_url == "https://example.com/page"


def test_page_title_delegates(bp, mock_page):
    mock_page.title.return_value = "My Page"
    assert bp.page_title == "My Page"


# ── click delegates ───────────────────────────────────────────────────────────

def test_click_calls_locator_click(bp, mock_page):
    mock_locator = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_locator.wait_for.return_value = None

    bp.click("#button")
    mock_locator.click.assert_called_once()


# ── navigate concatenation with base_url ─────────────────────────────────────

def test_navigate_concatenates_correctly(mock_page):
    bp = BasePage(mock_page, "https://app.example.com")
    bp.navigate("/about")
    mock_page.goto.assert_called_once_with("https://app.example.com/about", wait_until="networkidle")
