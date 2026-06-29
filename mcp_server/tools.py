"""
Low-level tool implementations for the MCP server.

DOMInspector and ApplicationProber use async Playwright so they run inside
the async event loop that FastMCP manages. Each per-element extraction is
wrapped in its own try/except so one bad node never aborts the whole inspection.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

# Allow direct import of sibling packages when server.py inserts repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory_engine import MemoryEngine
from utils.helpers import is_safe_probe_url

_shared_memory = MemoryEngine()


# ── DOM Inspector ─────────────────────────────────────────────────────────────

class DOMInspector:
    """Inspect the live DOM of any URL using a headless Chromium instance."""

    async def inspect(self, url: str, selector: str = "body") -> dict[str, Any]:
        # Validate URL before launching any browser
        safe, reason = is_safe_probe_url(url)
        if not safe:
            return {"status": "error", "url": url, "selector": selector, "error": reason}
        # Validate selector: must be a non-empty string, not over-long
        if not isinstance(selector, str) or not selector.strip():
            return {"status": "error", "url": url, "selector": selector,
                    "error": "selector must be a non-empty string"}
        if len(selector) > 1024:
            return {"status": "error", "url": url, "selector": selector,
                    "error": "selector exceeds maximum allowed length of 1024 characters"}
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30_000)
                locator = page.locator(selector)
                total = await locator.count()

                elements: list[dict] = []
                for i in range(min(total, 25)):
                    el = locator.nth(i)
                    element_data: dict[str, Any] = {"index": i}
                    try:
                        element_data["tag"] = await el.evaluate("el => el.tagName.toLowerCase()")
                    except Exception:
                        element_data["tag"] = "unknown"
                    try:
                        element_data["text"] = (await el.inner_text())[:200]
                    except Exception:
                        element_data["text"] = ""
                    try:
                        element_data["attributes"] = await el.evaluate(
                            "el => Object.fromEntries([...el.attributes].map(a => [a.name, a.value]))"
                        )
                    except Exception:
                        element_data["attributes"] = {}
                    try:
                        element_data["children"] = await el.evaluate("el => el.children.length")
                    except Exception:
                        element_data["children"] = 0
                    try:
                        bbox = await el.bounding_box()
                        element_data["visible"] = bbox is not None
                        element_data["bounding_box"] = bbox
                    except Exception:
                        element_data["visible"] = False
                        element_data["bounding_box"] = None

                    elements.append(element_data)

                return {
                    "status": "ok",
                    "url": url,
                    "final_url": page.url,
                    "page_title": await page.title(),
                    "selector": selector,
                    "total_matches": total,
                    "elements": elements,
                }
            except Exception as exc:
                return {"status": "error", "url": url, "selector": selector, "error": str(exc)}
            finally:
                await browser.close()


# ── Application Prober ────────────────────────────────────────────────────────

class ApplicationProber:
    """Deep-scan a page to surface its full interactive element tree."""

    async def probe(self, url: str, depth: int = 2) -> dict[str, Any]:
        # Validate URL before launching any browser
        safe, reason = is_safe_probe_url(url)
        if not safe:
            return {"status": "error", "url": url, "error": reason}
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=30_000)

                interactive: list[dict] = await page.evaluate("""() => {
                    const sel = [
                        'button', 'a[href]', 'input', 'select', 'textarea',
                        '[role="button"]', '[role="link"]', '[role="tab"]',
                        '[role="menuitem"]', '[tabindex]'
                    ].join(', ');
                    return Array.from(document.querySelectorAll(sel)).slice(0, 60).map(el => ({
                        tag:        el.tagName.toLowerCase(),
                        type:       el.type || null,
                        id:         el.id || null,
                        name:       el.name || null,
                        class:      (el.className || '').toString().slice(0, 80),
                        text:       (el.innerText || '').trim().slice(0, 120),
                        placeholder: el.placeholder || null,
                        href:       el.href || null,
                        role:       el.getAttribute('role') || null,
                        ariaLabel:  el.getAttribute('aria-label') || null,
                        dataTestId: el.getAttribute('data-testid') || null,
                        visible:    el.offsetParent !== null,
                    }));
                }""")

                forms: list[dict] = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll('form')).map(f => ({
                        id:     f.id || null,
                        action: f.action || null,
                        method: f.method || 'get',
                        fields: Array.from(f.querySelectorAll('input, select, textarea')).map(i => ({
                            name:        i.name || null,
                            type:        i.type || null,
                            id:          i.id || null,
                            required:    i.required,
                            placeholder: i.placeholder || null,
                            label:       document.querySelector(`label[for="${i.id}"]`)?.innerText || null,
                        }))
                    }))
                """)

                nav: list[dict] = await page.evaluate("""() =>
                    Array.from(document.querySelectorAll(
                        'nav a, header a, [role="navigation"] a'
                    )).slice(0, 20).map(a => ({
                        text: (a.innerText || '').trim(),
                        href: a.href,
                    }))
                """)

                meta: dict = await page.evaluate("""() => ({
                    title:       document.title,
                    description: document.querySelector('meta[name="description"]')?.content || null,
                    h1:  Array.from(document.querySelectorAll('h1')).map(h => h.innerText.trim()),
                    h2:  Array.from(document.querySelectorAll('h2')).slice(0,5).map(h => h.innerText.trim()),
                })""")

                return {
                    "status": "ok",
                    "url": url,
                    "final_url": page.url,
                    "meta": meta,
                    "interactive_elements": interactive,
                    "forms": forms,
                    "navigation": nav,
                    "summary": {
                        "interactive": len(interactive),
                        "forms": len(forms),
                        "nav_links": len(nav),
                    },
                }
            except Exception as exc:
                return {"status": "error", "url": url, "error": str(exc)}
            finally:
                await browser.close()


# ── Memory Tool ───────────────────────────────────────────────────────────────

class MemoryTool:
    """Wraps MemoryEngine for use by MCP tool handler functions."""

    def __init__(self) -> None:
        self._mem = _shared_memory

    def read(self, query: str = "", category: str = "") -> dict[str, Any]:
        if query:
            results = self._mem.search(query)
        elif category:
            results = self._mem.recall_by_category(category)
        else:
            results = list(self._mem._store.values())
        return {"query": query, "category": category, "count": len(results), "entries": results}

    def write(
        self,
        key: str,
        value: str,
        category: str = "general",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        eid = self._mem.remember(key=key, value=value, category=category, tags=tags or [])
        return {"status": "ok", "id": eid, "key": key, "category": category}

    def record_fix(
        self,
        page_name: str,
        element_name: str,
        original: str,
        fixed: str,
        reason: str,
    ) -> dict[str, Any]:
        eid = self._mem.record_selector_fix(page_name, element_name, original, fixed, reason)
        return {"status": "ok", "id": eid, "message": f"Fix recorded for {page_name}.{element_name}"}
