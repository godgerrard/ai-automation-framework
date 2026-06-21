"""Locators for SauceDemo checkout steps one, two, and complete."""


class CheckoutLocators:
    # ── Step 1: Information ───────────────────────────────────────────────────
    FIRST_NAME: str = "[data-test='firstName']"
    LAST_NAME: str = "[data-test='lastName']"
    POSTAL_CODE: str = "[data-test='postalCode']"
    CONTINUE_BTN: str = "[data-test='continue']"
    CANCEL_BTN: str = "[data-test='cancel']"
    ERROR_MESSAGE: str = "[data-test='error']"
    ERROR_DISMISS: str = ".error-button"

    # ── Step 2: Overview ──────────────────────────────────────────────────────
    ITEM_TOTAL_LABEL: str = ".summary_subtotal_label"
    TAX_LABEL: str = ".summary_tax_label"
    TOTAL_LABEL: str = ".summary_total_label"
    FINISH_BTN: str = "[data-test='finish']"
    ORDER_SUMMARY_ITEMS: str = ".cart_item"

    # ── Complete ──────────────────────────────────────────────────────────────
    COMPLETE_HEADER: str = "[data-test='complete-header']"
    COMPLETE_TEXT: str = "[data-test='complete-text']"
    BACK_HOME_BTN: str = "[data-test='back-to-products']"
    PONY_EXPRESS_IMG: str = ".pony_express"
