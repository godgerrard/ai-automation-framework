"""Page Object for the SauceDemo shopping cart page."""
from __future__ import annotations

from playwright.sync_api import Page

from core.base_page import BasePage
from locators.cart_locators import CartLocators


class CartPage(BasePage):
    """Page Object for /cart.html."""

    URL_PATH: str = "/cart.html"

    def __init__(self, page: Page, base_url: str = "https://www.saucedemo.com") -> None:
        super().__init__(page, base_url)

    def navigate_to(self) -> None:
        self.navigate(self.URL_PATH)

    def is_loaded(self) -> bool:
        return self.is_visible(CartLocators.CHECKOUT_BTN)

    def get_page_title(self) -> str:
        return self.get_text(CartLocators.PAGE_TITLE)

    # ── Item queries ───────────────────────────────────────────────────────────

    def get_item_count(self) -> int:
        return self.count_elements(CartLocators.CART_ITEMS)

    def get_item_names(self) -> list[str]:
        return [el.inner_text() for el in self.get_all_elements(CartLocators.CART_ITEM_NAME)]

    def get_item_prices(self) -> list[str]:
        return [el.inner_text() for el in self.get_all_elements(CartLocators.CART_ITEM_PRICE)]

    def is_item_in_cart(self, item_name: str) -> bool:
        return item_name in self.get_item_names()

    # ── Actions ────────────────────────────────────────────────────────────────

    def remove_item_by_slug(self, item_slug: str) -> None:
        self.click(f"[data-test='remove-{item_slug}']")

    def proceed_to_checkout(self) -> None:
        self.click(CartLocators.CHECKOUT_BTN)

    def continue_shopping(self) -> None:
        self.click(CartLocators.CONTINUE_SHOPPING_BTN)
