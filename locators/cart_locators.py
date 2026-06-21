"""Locators for the SauceDemo cart page."""


class CartLocators:
    PAGE_TITLE: str = ".title"
    CART_ITEMS: str = ".cart_item"
    CART_ITEM_NAME: str = ".inventory_item_name"
    CART_ITEM_PRICE: str = ".inventory_item_price"
    CART_ITEM_QUANTITY: str = ".cart_quantity"

    REMOVE_BTN: str = "[data-test^='remove-']"
    CHECKOUT_BTN: str = "[data-test='checkout']"
    CONTINUE_SHOPPING_BTN: str = "[data-test='continue-shopping']"

    CART_QUANTITY_LABEL: str = ".cart_quantity_label"
    CART_DESC_LABEL: str = ".cart_desc_label"
