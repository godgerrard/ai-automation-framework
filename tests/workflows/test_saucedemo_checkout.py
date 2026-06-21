"""
Test suite: SauceDemo Checkout Flow

Target : https://www.saucedemo.com
Covers : full golden-path checkout, cart item verification, remove from cart,
         empty-info validation errors, cancel returns to correct page,
         order confirmation details.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from pages.saucedemo_login_page import SauceDemoLoginPage
from pages.inventory_page import InventoryPage
from pages.cart_page import CartPage
from pages.checkout_page import CheckoutPage

BASE_URL = "https://www.saucedemo.com"
VALID_USER = "standard_user"
VALID_PASS = "secret_sauce"

_BACKPACK_SLUG = "sauce-labs-backpack"
_BACKPACK_NAME = "Sauce Labs Backpack"
_BIKE_SLUG = "sauce-labs-bike-light"


def _login_and_add(page: Page, *slugs: str) -> CartPage:
    """Login, add named items, navigate to cart, return CartPage."""
    login = SauceDemoLoginPage(page, BASE_URL)
    login.navigate_to()
    login.login(VALID_USER, VALID_PASS)

    inv = InventoryPage(page, BASE_URL)
    for slug in slugs:
        inv.add_item_by_name(slug)
    inv.go_to_cart()
    return CartPage(page, BASE_URL)


@pytest.mark.checkout
@pytest.mark.smoke
class TestCartPage:
    """Cart page: items present, counts, removal."""

    def test_cart_shows_added_item(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        assert cart.is_loaded()
        assert cart.is_item_in_cart(_BACKPACK_NAME), f"'{_BACKPACK_NAME}' not in cart"

    def test_cart_item_count_matches_added(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG, _BIKE_SLUG)
        assert cart.get_item_count() == 2, f"Expected 2 items, got {cart.get_item_count()}"

    def test_cart_items_have_prices(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        prices = cart.get_item_prices()
        assert len(prices) == 1
        assert "$" in prices[0], f"Price missing $ sign: {prices[0]!r}"

    def test_remove_item_from_cart(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        assert cart.get_item_count() == 1
        cart.remove_item_by_slug(_BACKPACK_SLUG)
        assert cart.get_item_count() == 0, "Cart should be empty after removal"

    def test_continue_shopping_returns_to_inventory(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.continue_shopping()
        assert "inventory.html" in cart.current_url


@pytest.mark.checkout
@pytest.mark.regression
class TestCheckoutInfoStep:
    """Checkout step 1: form validation and error messages."""

    def test_empty_form_shows_first_name_error(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.continue_to_overview()
        assert checkout.is_error_visible(), "Expected validation error"
        assert "first name" in checkout.get_error_message().lower()

    def test_missing_last_name_shows_error(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "", "")
        checkout.continue_to_overview()
        assert checkout.is_error_visible()
        assert "last name" in checkout.get_error_message().lower()

    def test_missing_postal_code_shows_error(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "")
        checkout.continue_to_overview()
        assert checkout.is_error_visible()
        assert "postal" in checkout.get_error_message().lower()

    def test_error_is_dismissible(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.continue_to_overview()
        assert checkout.is_error_visible()
        checkout.dismiss_error()
        assert not checkout.is_error_visible()

    def test_cancel_checkout_returns_to_cart(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.cancel_checkout()
        assert "cart.html" in checkout.current_url


@pytest.mark.checkout
@pytest.mark.smoke
class TestCheckoutGoldenPath:
    """Full end-to-end checkout — the golden path."""

    def test_valid_info_advances_to_overview(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "12345")
        checkout.continue_to_overview()
        assert "checkout-step-two" in checkout.current_url, (
            f"Expected step 2, got: {checkout.current_url}"
        )

    def test_overview_shows_correct_item_count(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "12345")
        checkout.continue_to_overview()
        assert checkout.get_summary_item_count() == 1

    def test_overview_shows_total_price(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "12345")
        checkout.continue_to_overview()
        total = checkout.get_total()
        assert "Total:" in total, f"Total label missing: {total!r}"
        assert "$" in total, f"Total missing price: {total!r}"

    def test_overview_shows_tax(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "12345")
        checkout.continue_to_overview()
        tax = checkout.get_tax()
        assert "Tax:" in tax and "$" in tax, f"Tax label unexpected: {tax!r}"

    def test_full_checkout_ends_on_complete_page(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "12345")
        checkout.continue_to_overview()
        checkout.finish_order()
        assert "checkout-complete" in checkout.current_url, (
            f"Expected complete page, got: {checkout.current_url}"
        )

    def test_order_complete_shows_success_header(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "12345")
        checkout.continue_to_overview()
        checkout.finish_order()
        assert checkout.is_order_complete(), "Order complete header not visible"
        header = checkout.get_complete_header()
        assert "thank you" in header.lower(), f"Unexpected header: {header!r}"

    def test_back_to_products_after_order(self, page: Page, memory) -> None:
        cart = _login_and_add(page, _BACKPACK_SLUG)
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Test", "User", "12345")
        checkout.continue_to_overview()
        checkout.finish_order()
        checkout.back_to_products()
        assert "inventory.html" in checkout.current_url

    def test_multi_item_checkout_golden_path(self, page: Page, memory) -> None:
        """Add two items, complete full checkout."""
        cart = _login_and_add(page, _BACKPACK_SLUG, _BIKE_SLUG)
        assert cart.get_item_count() == 2
        cart.proceed_to_checkout()
        checkout = CheckoutPage(page, BASE_URL)
        checkout.fill_info("Jane", "Doe", "90210")
        checkout.continue_to_overview()
        assert checkout.get_summary_item_count() == 2
        checkout.finish_order()
        assert checkout.is_order_complete()
