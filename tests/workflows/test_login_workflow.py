"""
Test suite: User Login Flow (story ID: login_001)

Generated from: stories/login_user_story.json
Covers: happy-path login, invalid credentials, empty-form validation, page accessibility.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from pages.login_page import LoginPage


@pytest.mark.authentication
@pytest.mark.smoke
class TestLoginWorkflow:
    """Regression suite for User Login Flow."""

    def test_successful_login_redirects_to_dashboard(self, page: Page, base_url: str) -> None:
        """Happy-path: registered user logs in with valid credentials."""
        login = LoginPage(page, base_url)
        login.navigate_to()
        assert login.is_loaded(), "Login page did not load"

        login.login("test@example.com", "SecurePass123!")
        login.wait_for_url("**/dashboard")

        assert "/dashboard" in login.current_url, (
            f"Expected redirect to /dashboard, got: {login.current_url}"
        )

    def test_invalid_credentials_show_error(self, page: Page, base_url: str) -> None:
        """Negative: wrong credentials must surface an error message."""
        login = LoginPage(page, base_url)
        login.navigate_to()
        login.login("invalid@example.com", "WrongPassword!")

        assert login.is_error_visible(), "Error message not displayed for invalid credentials"
        assert "/dashboard" not in login.current_url, "User should NOT be redirected after failed login"

    def test_empty_form_shows_validation_errors(self, page: Page, base_url: str) -> None:
        """Negative: submitting an empty form must trigger field-level validation."""
        login = LoginPage(page, base_url)
        login.navigate_to()
        login.click_submit()

        assert login.is_error_visible(), "Expected validation error after empty form submission"

    def test_page_elements_are_present(self, page: Page, base_url: str) -> None:
        """Smoke: all critical elements must be rendered on page load."""
        from locators.login_locators import LoginLocators

        login = LoginPage(page, base_url)
        login.navigate_to()

        assert login.is_visible(LoginLocators.EMAIL_FIELD), "Email field missing"
        assert login.is_visible(LoginLocators.PASSWORD_FIELD), "Password field missing"
        assert login.is_visible(LoginLocators.SUBMIT_BUTTON), "Submit button missing"

    def test_forgot_password_link_navigates(self, page: Page, base_url: str) -> None:
        """Navigation: forgot-password link must navigate away from the login page."""
        login = LoginPage(page, base_url)
        login.navigate_to()
        login.click_forgot_password()

        assert login.current_url != f"{base_url}/login", (
            "Forgot-password link did not navigate away from the login page"
        )
