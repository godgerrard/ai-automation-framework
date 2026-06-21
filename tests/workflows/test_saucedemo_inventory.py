"""
Test suite: SauceDemo Inventory / Product Listing

Target : https://www.saucedemo.com/inventory.html
Covers : page load, product count, add-to-cart, cart badge, sorting, logout,
         unauthenticated access redirect.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from pages.saucedemo_login_page import SauceDemoLoginPage
from pages.inventory_page import InventoryPage
from locators.inventory_locators import InventoryLocators

BASE_URL = "https://www.saucedemo.com"
VALID_USER = "standard_user"
VALID_PASS = "secret_sauce"


def _login(page: Page) -> InventoryPage:
    """Helper: log in and return an InventoryPage ready to use."""
    login = SauceDemoLoginPage(page, BASE_URL)
    login.navigate_to()
    login.login(VALID_USER, VALID_PASS)
    return InventoryPage(page, BASE_URL)


@pytest.mark.smoke
class TestInventoryPageLoad:
    """Smoke: verify the inventory page loads correctly."""

    def test_inventory_page_loads_after_login(self, page: Page, memory) -> None:
        inv = _login(page)
        assert inv.is_loaded(), "Inventory list not visible after login"

    def test_inventory_page_title_is_products(self, page: Page, memory) -> None:
        inv = _login(page)
        assert inv.get_page_title() == "Products", (
            f"Expected 'Products', got {inv.get_page_title()!r}"
        )

    def test_inventory_shows_six_products(self, page: Page, memory) -> None:
        inv = _login(page)
        count = inv.get_product_count()
        assert count == 6, f"Expected 6 products, found {count}"

    def test_all_products_have_names(self, page: Page, memory) -> None:
        inv = _login(page)
        names = inv.get_product_names()
        assert len(names) == 6
        for name in names:
            assert name.strip(), f"Found blank product name: {name!r}"

    def test_all_products_have_prices(self, page: Page, memory) -> None:
        inv = _login(page)
        prices = inv.get_product_prices()
        assert len(prices) == 6
        for price in prices:
            assert price > 0, f"Product price should be > 0, got {price}"


@pytest.mark.regression
class TestCartInteraction:
    """Add-to-cart, badge updates, and cart navigation."""

    def test_cart_badge_not_visible_before_adding(self, page: Page, memory) -> None:
        inv = _login(page)
        count = inv.get_cart_badge_count()
        assert count == 0, f"Cart badge should be 0, got {count}"

    def test_add_first_item_updates_badge_to_one(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.add_item_by_index(0)
        assert inv.get_cart_badge_count() == 1

    def test_add_two_items_badge_shows_two(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.add_item_by_index(0)
        inv.add_item_by_index(1)
        assert inv.get_cart_badge_count() == 2

    def test_add_item_changes_button_to_remove(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.add_item_by_name("sauce-labs-backpack")
        assert inv.is_visible("[data-test='remove-sauce-labs-backpack']"), (
            "Remove button not visible after add-to-cart"
        )

    def test_go_to_cart_navigates_correctly(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.add_item_by_index(0)
        inv.go_to_cart()
        assert "cart.html" in inv.current_url


@pytest.mark.regression
class TestProductSorting:
    """Sort functionality: name and price."""

    def test_sort_name_az_is_default_order(self, page: Page, memory) -> None:
        inv = _login(page)
        names = inv.get_product_names()
        assert names == sorted(names), f"Default A-Z sort not matched: {names}"

    def test_sort_name_za_reverses_order(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.sort_by("za")
        names = inv.get_product_names()
        assert names == sorted(names, reverse=True), f"Z-A sort failed: {names}"

    def test_sort_price_low_to_high(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.sort_by("lohi")
        prices = inv.get_product_prices()
        assert prices == sorted(prices), f"Low-to-high price sort failed: {prices}"

    def test_sort_price_high_to_low(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.sort_by("hilo")
        prices = inv.get_product_prices()
        assert prices == sorted(prices, reverse=True), f"High-to-low price sort failed: {prices}"


@pytest.mark.authentication
class TestInventoryAccess:
    """Auth guards and logout."""

    def test_unauthenticated_access_redirects_to_login(self, page: Page, memory) -> None:
        inv = InventoryPage(page, BASE_URL)
        inv.navigate_to()
        assert "inventory" not in inv.current_url, (
            "Should not access inventory without login"
        )

    def test_logout_from_inventory(self, page: Page, memory) -> None:
        inv = _login(page)
        inv.logout()
        assert "inventory" not in inv.current_url, "Should be logged out"
        login_page = SauceDemoLoginPage(page, BASE_URL)
        assert login_page.is_loaded(), "Should return to login page after logout"
