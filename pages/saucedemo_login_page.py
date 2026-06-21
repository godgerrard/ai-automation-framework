"""Page Object for the SauceDemo login page (https://www.saucedemo.com)."""
from __future__ import annotations

from playwright.sync_api import Page

from core.base_page import BasePage
from locators.saucedemo_login_locators import SauceDemoLoginLocators


class SauceDemoLoginPage(BasePage):
    """Page Object for https://www.saucedemo.com (login screen)."""

    URL_PATH: str = "/"

    def __init__(self, page: Page, base_url: str = "https://www.saucedemo.com") -> None:
        super().__init__(page, base_url)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to(self) -> None:
        self.navigate(self.URL_PATH)

    def is_loaded(self) -> bool:
        return self.is_visible(SauceDemoLoginLocators.LOGIN_WRAPPER)

    # ── Actions ────────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> None:
        self.fill(SauceDemoLoginLocators.USERNAME_FIELD, username)
        self.fill(SauceDemoLoginLocators.PASSWORD_FIELD, password)
        self.click(SauceDemoLoginLocators.LOGIN_BUTTON)

    def enter_username(self, username: str) -> None:
        self.fill(SauceDemoLoginLocators.USERNAME_FIELD, username)

    def enter_password(self, password: str) -> None:
        self.fill(SauceDemoLoginLocators.PASSWORD_FIELD, password)

    def click_login(self) -> None:
        self.click(SauceDemoLoginLocators.LOGIN_BUTTON)

    def dismiss_error(self) -> None:
        self.click(SauceDemoLoginLocators.ERROR_DISMISS)

    # ── Queries ────────────────────────────────────────────────────────────────

    def is_error_visible(self) -> bool:
        return self.is_visible(SauceDemoLoginLocators.ERROR_MESSAGE)

    def get_error_message(self) -> str:
        return self.get_text(SauceDemoLoginLocators.ERROR_MESSAGE)

    def get_username_value(self) -> str:
        return self.get_value(SauceDemoLoginLocators.USERNAME_FIELD)
