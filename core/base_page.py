"""
BasePage — every Page Object inherits from this class.
Wraps Playwright primitives with explicit waits, logging, and a uniform action API.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class BasePage:
    def __init__(self, page: Page, base_url: str = "", timeout: int = 30_000) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Navigation ────────────────────────────────────────────────────────────

    def navigate(self, path: str = "") -> None:
        url = f"{self.base_url}{path}" if path else self.base_url
        self.page.goto(url, wait_until="networkidle")
        logger.info("Navigated to: %s", url)

    def wait_for_url(self, pattern: str, timeout: Optional[int] = None) -> None:
        self.page.wait_for_url(pattern, timeout=timeout or self.timeout)

    def wait_for_navigation(self) -> None:
        self.page.wait_for_load_state("networkidle")

    # ── Element resolution ────────────────────────────────────────────────────

    def locate(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def wait_for_element(
        self,
        selector: str,
        state: str = "visible",
        timeout: Optional[int] = None,
    ) -> Locator:
        locator = self.page.locator(selector)
        locator.wait_for(state=state, timeout=timeout or self.timeout)
        return locator

    # ── Actions ───────────────────────────────────────────────────────────────

    def click(self, selector: str, timeout: Optional[int] = None) -> None:
        self.wait_for_element(selector, "visible", timeout).click()
        logger.debug("Clicked: %s", selector)

    def fill(self, selector: str, value: str, timeout: Optional[int] = None) -> None:
        el = self.wait_for_element(selector, "visible", timeout)
        el.clear()
        el.fill(value)
        logger.debug("Filled '%s'", selector)

    def select_option(self, selector: str, value: str) -> None:
        self.page.locator(selector).select_option(value)

    def hover(self, selector: str) -> None:
        self.wait_for_element(selector, "visible").hover()

    def scroll_to(self, selector: str) -> None:
        self.page.locator(selector).scroll_into_view_if_needed()

    def press_key(self, selector: str, key: str) -> None:
        self.page.locator(selector).press(key)

    def double_click(self, selector: str) -> None:
        self.wait_for_element(selector, "visible").dblclick()

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_text(self, selector: str, timeout: Optional[int] = None) -> str:
        return self.wait_for_element(selector, "visible", timeout).inner_text()

    def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        return self.page.locator(selector).get_attribute(attribute)

    def get_all_elements(self, selector: str) -> List[Locator]:
        return self.page.locator(selector).all()

    def count_elements(self, selector: str) -> int:
        return self.page.locator(selector).count()

    def get_value(self, selector: str) -> str:
        return self.page.locator(selector).input_value()

    # ── State checks ──────────────────────────────────────────────────────────

    def is_visible(self, selector: str, timeout: int = 5_000) -> bool:
        try:
            self.page.locator(selector).wait_for(state="visible", timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False

    def is_enabled(self, selector: str) -> bool:
        return self.page.locator(selector).is_enabled()

    def is_checked(self, selector: str) -> bool:
        return self.page.locator(selector).is_checked()

    def wait_for_text(
        self, selector: str, text: str, timeout: Optional[int] = None
    ) -> None:
        self.page.locator(selector).filter(has_text=text).wait_for(
            state="visible", timeout=timeout or self.timeout
        )

    # ── Page-level ────────────────────────────────────────────────────────────

    @property
    def current_url(self) -> str:
        return self.page.url

    @property
    def page_title(self) -> str:
        return self.page.title()

    def take_screenshot(self, path: str) -> None:
        self.page.screenshot(path=path, full_page=True)
        logger.info("Screenshot saved: %s", path)

    def reload(self) -> None:
        self.page.reload(wait_until="networkidle")
