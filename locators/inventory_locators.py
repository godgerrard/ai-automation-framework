"""Locators for the SauceDemo inventory (product listing) page."""


class InventoryLocators:
    # Page structure
    INVENTORY_LIST: str = ".inventory_list"
    INVENTORY_ITEM: str = ".inventory_item"
    PAGE_TITLE: str = ".title"

    # Per-item elements
    ITEM_NAME: str = ".inventory_item_name"
    ITEM_PRICE: str = ".inventory_item_price"
    ITEM_DESC: str = ".inventory_item_desc"

    # Cart interaction
    ADD_TO_CART_BTN: str = "[data-test^='add-to-cart']"
    REMOVE_BTN: str = "[data-test^='remove-']"
    CART_BADGE: str = ".shopping_cart_badge"
    CART_LINK: str = ".shopping_cart_link"

    # Sorting
    SORT_DROPDOWN: str = "[data-test='product-sort-container']"

    # Burger menu / logout
    BURGER_MENU_BTN: str = "#react-burger-menu-btn"
    BURGER_MENU_CLOSE: str = "#react-burger-cross-btn"
    LOGOUT_LINK: str = "#logout_sidebar_link"
    ALL_ITEMS_LINK: str = "#inventory_sidebar_link"
    ABOUT_LINK: str = "#about_sidebar_link"
    RESET_LINK: str = "#reset_sidebar_link"
