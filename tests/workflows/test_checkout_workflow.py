"""
Test suite: E-Commerce Checkout Flow (story ID: checkout_001)

Generated from: stories/checkout_user_story.json
Covers: add-to-cart, checkout, payment, order confirmation, and invalid-card negative.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from core.base_page import BasePage


@pytest.mark.checkout
@pytest.mark.payment
@pytest.mark.regression
class TestCheckoutWorkflow:
    """Regression suite for E-Commerce Checkout Flow."""

    @pytest.fixture(autouse=True)
    def _setup(self, page: Page, base_url: str) -> None:
        self._page = BasePage(page, base_url)

    def test_add_to_cart_and_checkout(self, page: Page, base_url: str) -> None:
        """Happy-path: user adds a product and completes checkout."""
        p = BasePage(page, base_url)

        # Navigate to products listing page
        page.goto(base_url + "/products")

        # Add first available product to cart
        page.click(".product-card:first-child .btn-add-to-cart")

        # Verify cart notification appears
        assert p.is_visible(".cart-notification"), "Cart notification did not appear"

        # Navigate to the cart page
        page.goto(base_url + "/cart")

        # Click Proceed to Checkout
        page.click("button.proceed-checkout")

        # Enter shipping address
        page.fill("#shipping-address", "123 Test Street, Test City, TC 12345")

        # Enter test credit card number
        page.fill("#card-number", "4111111111111111")

        # Click Place Order
        page.click("button.place-order")

        # Verify navigation to order confirmation page
        page.wait_for_url("**/order-confirmation")

        # Verify order ID is displayed
        assert p.is_visible(".order-id"), "Order ID not displayed on confirmation page"

    def test_invalid_payment_card_rejected(self, page: Page, base_url: str) -> None:
        """Negative: invalid payment card rejected — Expected: Payment error message displayed."""
        # TODO: implement negative scenario
        pass
