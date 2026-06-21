"""Page Object for SauceDemo checkout: step one, step two, and complete."""
from __future__ import annotations

from playwright.sync_api import Page

from core.base_page import BasePage
from locators.checkout_locators import CheckoutLocators


class CheckoutPage(BasePage):
    """Covers /checkout-step-one.html, /checkout-step-two.html, /checkout-complete.html."""

    URL_PATH_STEP1: str = "/checkout-step-one.html"
    URL_PATH_STEP2: str = "/checkout-step-two.html"
    URL_PATH_COMPLETE: str = "/checkout-complete.html"

    def __init__(self, page: Page, base_url: str = "https://www.saucedemo.com") -> None:
        super().__init__(page, base_url)

    # ── Step 1 ─────────────────────────────────────────────────────────────────

    def fill_info(self, first_name: str, last_name: str, postal_code: str) -> None:
        self.fill(CheckoutLocators.FIRST_NAME, first_name)
        self.fill(CheckoutLocators.LAST_NAME, last_name)
        self.fill(CheckoutLocators.POSTAL_CODE, postal_code)

    def continue_to_overview(self) -> None:
        self.click(CheckoutLocators.CONTINUE_BTN)

    def cancel_checkout(self) -> None:
        self.click(CheckoutLocators.CANCEL_BTN)

    def is_error_visible(self) -> bool:
        return self.is_visible(CheckoutLocators.ERROR_MESSAGE)

    def get_error_message(self) -> str:
        return self.get_text(CheckoutLocators.ERROR_MESSAGE)

    def dismiss_error(self) -> None:
        self.click(CheckoutLocators.ERROR_DISMISS)

    # ── Step 2 ─────────────────────────────────────────────────────────────────

    def get_item_total(self) -> str:
        return self.get_text(CheckoutLocators.ITEM_TOTAL_LABEL)

    def get_tax(self) -> str:
        return self.get_text(CheckoutLocators.TAX_LABEL)

    def get_total(self) -> str:
        return self.get_text(CheckoutLocators.TOTAL_LABEL)

    def get_summary_item_count(self) -> int:
        return self.count_elements(CheckoutLocators.ORDER_SUMMARY_ITEMS)

    def finish_order(self) -> None:
        self.click(CheckoutLocators.FINISH_BTN)

    # ── Complete ───────────────────────────────────────────────────────────────

    def is_order_complete(self) -> bool:
        return self.is_visible(CheckoutLocators.COMPLETE_HEADER)

    def get_complete_header(self) -> str:
        return self.get_text(CheckoutLocators.COMPLETE_HEADER)

    def get_complete_text(self) -> str:
        return self.get_text(CheckoutLocators.COMPLETE_TEXT)

    def back_to_products(self) -> None:
        self.click(CheckoutLocators.BACK_HOME_BTN)
