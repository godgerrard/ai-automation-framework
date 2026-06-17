"""
Page Object for the Login page.
Extends BasePage with login-specific actions and assertions.
"""
from __future__ import annotations

from playwright.sync_api import Page

from core.base_page import BasePage
from locators.login_locators import LoginLocators


class LoginPage(BasePage):
    """Encapsulates all interactions with the application login page."""

    URL_PATH: str = "/login"

    def __init__(self, page: Page, base_url: str = "") -> None:
        super().__init__(page, base_url)

    # ── Navigation ────────────────────────────────────────────────────────────

    def navigate_to(self) -> None:
        self.navigate(self.URL_PATH)

    # ── Actions ───────────────────────────────────────────────────────────────

    def enter_email(self, email: str) -> None:
        self.fill(LoginLocators.EMAIL_FIELD, email)

    def enter_password(self, password: str) -> None:
        self.fill(LoginLocators.PASSWORD_FIELD, password)

    def click_submit(self) -> None:
        self.click(LoginLocators.SUBMIT_BUTTON)

    def login(self, email: str, password: str) -> None:
        """Convenience: fills both fields and submits."""
        self.enter_email(email)
        self.enter_password(password)
        self.click_submit()

    def click_forgot_password(self) -> None:
        self.click(LoginLocators.FORGOT_PASSWORD_LINK)

    def click_register(self) -> None:
        self.click(LoginLocators.REGISTER_LINK)

    # ── Assertions / Queries ──────────────────────────────────────────────────

    def is_loaded(self) -> bool:
        return self.is_visible(LoginLocators.PAGE_INDICATOR)

    def get_heading(self) -> str:
        return self.get_text(LoginLocators.PAGE_HEADING)

    def is_error_visible(self) -> bool:
        return self.is_visible(LoginLocators.ERROR_MESSAGE)

    def get_error_text(self) -> str:
        return self.get_text(LoginLocators.ERROR_MESSAGE)

    def is_success_visible(self) -> bool:
        return self.is_visible(LoginLocators.SUCCESS_FLASH)
