"""
DriverFactory — owns the Playwright browser lifecycle.
Provides a context-manager for safe acquisition and release of browser pages.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from config import FrameworkConfig, load_config

logger = logging.getLogger(__name__)


class DriverFactory:
    def __init__(self, config: Optional[FrameworkConfig] = None) -> None:
        self.config = config or load_config()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        launcher = getattr(self._playwright, self.config.browser.browser)
        self._browser = launcher.launch(
            headless=self.config.browser.headless,
            slow_mo=self.config.browser.slow_mo,
        )
        logger.info("Browser started: %s (headless=%s)", self.config.browser.browser, self.config.browser.headless)

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Browser stopped.")

    def new_context(self) -> BrowserContext:
        if not self._browser:
            raise RuntimeError("Call start() before requesting a context.")
        return self._browser.new_context(viewport=self.config.browser.viewport)

    def new_page(self) -> Page:
        ctx = self.new_context()
        page = ctx.new_page()
        page.set_default_timeout(self.config.browser.timeout)
        return page

    @contextmanager
    def managed_page(self) -> Generator[Page, None, None]:
        self.start()
        try:
            yield self.new_page()
        finally:
            self.stop()


@contextmanager
def get_driver(config: Optional[FrameworkConfig] = None) -> Generator[Page, None, None]:
    """Convenience context-manager: get a page and auto-close the browser when done."""
    factory = DriverFactory(config)
    with factory.managed_page() as page:
        yield page
