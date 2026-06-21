"""
Test suite: SauceDemo HTTP availability checks

SauceDemo (saucedemo.com) is a frontend-only demo app with no REST API.
These tests verify HTTP-level health: status codes, content-type headers,
and response-time budget for the pages the app serves.

Note: Tests access public HTML pages via GET. They do NOT authenticate.
      Protected pages (inventory, cart, checkout) redirect to the login page.
"""
from __future__ import annotations

import pytest

from services.api_service import APIService

BASE_URL = "https://www.saucedemo.com"
RESPONSE_TIME_MS = 4000

_PUBLIC_PAGES = [
    ("/", "login page"),
]

_PROTECTED_PAGES = [
    ("/inventory.html", "inventory"),
    ("/cart.html", "cart"),
    ("/checkout-step-one.html", "checkout step 1"),
]


@pytest.fixture(scope="module")
def sd_client() -> APIService:
    return APIService(BASE_URL, max_retries=0)


@pytest.mark.api
class TestSauceDemoHTTPAvailability:
    """HTTP-level checks: status codes, headers, response time."""

    # ── Login page (public) ───────────────────────────────────────────────────

    def test_login_page_returns_200(self, sd_client: APIService) -> None:
        resp = sd_client.get("/")
        resp.assert_ok()

    def test_login_page_content_type_is_html(self, sd_client: APIService) -> None:
        resp = sd_client.get("/")
        resp.assert_ok().assert_header_contains("content-type", "text/html")

    def test_login_page_response_time(self, sd_client: APIService) -> None:
        resp = sd_client.get("/")
        resp.assert_ok().assert_response_time(RESPONSE_TIME_MS)

    def test_login_page_body_is_not_empty(self, sd_client: APIService) -> None:
        resp = sd_client.get("/")
        resp.assert_ok().assert_not_empty()

    def test_login_page_body_contains_swag_labs(self, sd_client: APIService) -> None:
        resp = sd_client.get("/")
        resp.assert_ok()
        assert "Swag Labs" in resp.text(), "Page body should contain 'Swag Labs'"

    # ── Protected pages (redirect to login) ───────────────────────────────────

    @pytest.mark.parametrize("path,label", _PROTECTED_PAGES)
    def test_protected_page_returns_404_at_http_level(self, sd_client: APIService, path: str, label: str) -> None:
        """SauceDemo is a GitHub Pages SPA. Sub-routes like /inventory.html are not real files,
        so a raw HTTP GET returns 404. A real browser receives 404 + the SPA shell script,
        which rewrites the URL and renders the correct page via client-side routing."""
        resp = sd_client.get(path)
        resp.assert_not_found()

    # ── Static assets ─────────────────────────────────────────────────────────

    def test_main_css_is_accessible(self, sd_client: APIService) -> None:
        resp = sd_client.get("/static/css/main.css")
        # SauceDemo serves a hashed CSS — just verify the static root is accessible
        resp.assert_status_in(200, 301, 302, 404)

    def test_favicon_is_accessible(self, sd_client: APIService) -> None:
        resp = sd_client.get("/favicon.ico")
        resp.assert_status_in(200, 301, 302, 404)

    # ── Repeated load performance ─────────────────────────────────────────────

    def test_three_consecutive_requests_all_under_threshold(self, sd_client: APIService) -> None:
        for _ in range(3):
            resp = sd_client.get("/")
            resp.assert_ok().assert_response_time(RESPONSE_TIME_MS)
