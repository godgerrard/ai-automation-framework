"""
Test suite: SauceDemo Login Flows

Target : https://www.saucedemo.com
Covers : happy-path login, locked-out user, empty/partial credentials,
         error message content, error dismissal, redirect after login.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from pages.saucedemo_login_page import SauceDemoLoginPage
from locators.saucedemo_login_locators import SauceDemoLoginLocators

BASE_URL = "https://www.saucedemo.com"
VALID_USER = "standard_user"
VALID_PASS = "secret_sauce"


@pytest.mark.authentication
@pytest.mark.smoke
class TestSauceDemoLogin:
    """Login page test suite for saucedemo.com."""

    # ── Smoke: page load ───────────────────────────────────────────────────────

    def test_login_page_loads(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        assert login.is_loaded(), "Login page wrapper not visible"

    def test_login_page_has_all_fields(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        assert login.is_visible(SauceDemoLoginLocators.USERNAME_FIELD), "Username field missing"
        assert login.is_visible(SauceDemoLoginLocators.PASSWORD_FIELD), "Password field missing"
        assert login.is_visible(SauceDemoLoginLocators.LOGIN_BUTTON), "Login button missing"

    def test_login_page_title(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        assert "Swag Labs" in login.page_title, f"Unexpected page title: {login.page_title!r}"

    # ── Happy path ─────────────────────────────────────────────────────────────

    def test_standard_user_can_login(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login(VALID_USER, VALID_PASS)
        assert "/inventory" in login.current_url, (
            f"Expected redirect to inventory, got: {login.current_url}"
        )

    def test_login_redirects_to_inventory_page(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login(VALID_USER, VALID_PASS)
        login.wait_for_url("**/inventory.html")
        assert "inventory.html" in login.current_url

    def test_no_error_shown_on_valid_login(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login(VALID_USER, VALID_PASS)
        assert not login.is_error_visible(), "Unexpected error after valid login"

    # ── Negative: locked-out user ─────────────────────────────────────────────

    def test_locked_out_user_cannot_login(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login("locked_out_user", VALID_PASS)
        assert login.is_error_visible(), "Expected error for locked_out_user"

    def test_locked_out_user_error_message_content(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login("locked_out_user", VALID_PASS)
        msg = login.get_error_message()
        assert "locked out" in msg.lower(), f"Unexpected error: {msg!r}"

    def test_locked_out_user_stays_on_login_page(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login("locked_out_user", VALID_PASS)
        assert "inventory" not in login.current_url

    # ── Negative: empty / partial credentials ─────────────────────────────────

    def test_empty_credentials_show_error(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.click_login()
        assert login.is_error_visible(), "Expected error on empty submit"

    def test_empty_username_error_content(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.click_login()
        msg = login.get_error_message()
        assert "username is required" in msg.lower(), f"Got: {msg!r}"

    def test_missing_password_shows_error(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.enter_username(VALID_USER)
        login.click_login()
        assert login.is_error_visible(), "Expected error with missing password"

    def test_missing_password_error_content(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.enter_username(VALID_USER)
        login.click_login()
        msg = login.get_error_message()
        assert "password is required" in msg.lower(), f"Got: {msg!r}"

    def test_wrong_password_shows_error(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login(VALID_USER, "wrong_password_xyz")
        assert login.is_error_visible(), "Expected error for wrong password"

    def test_wrong_password_does_not_redirect(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login(VALID_USER, "wrong_password_xyz")
        assert "inventory" not in login.current_url

    # ── Error dismissal ────────────────────────────────────────────────────────

    def test_error_can_be_dismissed(self, page: Page, memory) -> None:
        login = SauceDemoLoginPage(page, BASE_URL)
        login.navigate_to()
        login.login("locked_out_user", VALID_PASS)
        assert login.is_error_visible()
        login.dismiss_error()
        assert not login.is_error_visible(), "Error should be hidden after dismissal"
