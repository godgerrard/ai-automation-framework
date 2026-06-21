"""Page Object for the SauceDemo product inventory page."""
from __future__ import annotations

from playwright.sync_api import Page

from core.base_page import BasePage
from locators.inventory_locators import InventoryLocators


class InventoryPage(BasePage):
    """Page Object for /inventory.html — the main product listing."""

    URL_PATH: str = "/inventory.html"

    def __init__(self, page: Page, base_url: str = "https://www.saucedemo.com") -> None:
        super().__init__(page, base_url)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate_to(self) -> None:
        self.navigate(self.URL_PATH)

    def is_loaded(self) -> bool:
        return self.is_visible(InventoryLocators.INVENTORY_LIST)

    def get_page_title(self) -> str:
        return self.get_text(InventoryLocators.PAGE_TITLE)

    # ── Product interactions ───────────────────────────────────────────────────

    def get_product_count(self) -> int:
        return self.count_elements(InventoryLocators.INVENTORY_ITEM)

    def get_product_names(self) -> list[str]:
        return [el.inner_text() for el in self.get_all_elements(InventoryLocators.ITEM_NAME)]

    def get_product_prices(self) -> list[float]:
        return [
            float(el.inner_text().replace("$", "").strip())
            for el in self.get_all_elements(InventoryLocators.ITEM_PRICE)
        ]

    def add_item_by_index(self, index: int = 0) -> str:
        """Add the nth product to cart. Returns its name."""
        name_els = self.get_all_elements(InventoryLocators.ITEM_NAME)
        btn_els = self.get_all_elements(InventoryLocators.ADD_TO_CART_BTN)
        name = name_els[index].inner_text()
        btn_els[index].click()
        return name

    def add_item_by_name(self, item_slug: str) -> None:
        """Add a specific item using its data-test slug, e.g. 'sauce-labs-backpack'."""
        self.click(f"[data-test='add-to-cart-{item_slug}']")

    def remove_item_by_name(self, item_slug: str) -> None:
        self.click(f"[data-test='remove-{item_slug}']")

    # ── Cart ───────────────────────────────────────────────────────────────────

    def get_cart_badge_count(self) -> int:
        if not self.is_visible(InventoryLocators.CART_BADGE, timeout=2000):
            return 0
        return int(self.get_text(InventoryLocators.CART_BADGE))

    def go_to_cart(self) -> None:
        self.click(InventoryLocators.CART_LINK)

    # ── Sorting ────────────────────────────────────────────────────────────────

    def sort_by(self, option: str) -> None:
        """Sort products. option: 'az' | 'za' | 'lohi' | 'hilo'"""
        self.select_option(InventoryLocators.SORT_DROPDOWN, option)

    # ── Menu / logout ──────────────────────────────────────────────────────────

    def open_menu(self) -> None:
        self.click(InventoryLocators.BURGER_MENU_BTN)
        self.wait_for_element(InventoryLocators.LOGOUT_LINK)

    def logout(self) -> None:
        self.open_menu()
        self.click(InventoryLocators.LOGOUT_LINK)

    def reset_app_state(self) -> None:
        self.open_menu()
        self.click(InventoryLocators.RESET_LINK)
        self.click(InventoryLocators.BURGER_MENU_CLOSE)
