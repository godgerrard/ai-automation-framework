"""
APIResponse — immutable HTTP response wrapper with a fluent, chainable assertion API.

Every HTTP method in APIService returns an APIResponse.  Tests chain assertions:

    api.get("/users/1")
       .assert_status(200)
       .assert_json_key_exists("data", "support")
       .assert_response_time(1500)

Design rules:
  - Every assert_* method returns self so chains stay readable.
  - Error messages always include method + URL + expected vs actual.
  - extract() pulls a value from the body for use in the next request (chaining).
  - No external dependencies — pure stdlib.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Type

logger = logging.getLogger(__name__)


class APIResponse:
    """Immutable HTTP response with a fluent assertion API."""

    def __init__(
        self,
        status_code: int,
        body: bytes,
        headers: dict[str, str],
        elapsed_ms: float,
        url: str,
        method: str,
    ) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.elapsed_ms = elapsed_ms
        self.url = url
        self.method = method
        logger.debug("%s %s → %d (%.0fms)", method, url, status_code, elapsed_ms)

    # ── Raw accessors ──────────────────────────────────────────────────────────

    def json(self) -> Any:
        """Deserialize body as JSON. Raises json.JSONDecodeError if body is not JSON."""
        return json.loads(self._body)

    def text(self) -> str:
        return self._body.decode("utf-8")

    def is_empty(self) -> bool:
        return not self._body or self._body.strip() in (b"", b"null")

    # ── Status assertions ──────────────────────────────────────────────────────

    def assert_status(self, expected: int) -> "APIResponse":
        assert self.status_code == expected, (
            f"{self.method} {self.url}\n"
            f"  Expected HTTP {expected}, got {self.status_code}\n"
            f"  Body: {self.text()[:400]}"
        )
        return self

    def assert_ok(self) -> "APIResponse":
        return self.assert_status(200)

    def assert_created(self) -> "APIResponse":
        return self.assert_status(201)

    def assert_no_content(self) -> "APIResponse":
        return self.assert_status(204)

    def assert_not_found(self) -> "APIResponse":
        return self.assert_status(404)

    def assert_unauthorized(self) -> "APIResponse":
        return self.assert_status(401)

    def assert_bad_request(self) -> "APIResponse":
        return self.assert_status(400)

    def assert_status_in(self, *codes: int) -> "APIResponse":
        assert self.status_code in codes, (
            f"{self.method} {self.url}\n"
            f"  Expected one of {codes}, got {self.status_code}\n"
            f"  Body: {self.text()[:400]}"
        )
        return self

    # ── Body assertions ────────────────────────────────────────────────────────

    def assert_not_empty(self) -> "APIResponse":
        assert not self.is_empty(), (
            f"{self.method} {self.url} — response body is empty"
        )
        return self

    def assert_json_key_exists(self, *keys: str) -> "APIResponse":
        body = self.json()
        for key in keys:
            assert key in body, (
                f"{self.method} {self.url}\n"
                f"  Expected key '{key}' in body. Present: {list(body.keys())}"
            )
        return self

    def assert_json_key(self, key: str, expected: Any) -> "APIResponse":
        body = self.json()
        assert key in body, (
            f"{self.method} {self.url} — key '{key}' not found. "
            f"Present: {list(body.keys())}"
        )
        assert body[key] == expected, (
            f"{self.method} {self.url}\n"
            f"  Key '{key}': expected {expected!r}, got {body[key]!r}"
        )
        return self

    def assert_json_key_type(self, key: str, expected_type: Type) -> "APIResponse":
        body = self.json()
        assert key in body, f"Key '{key}' not found in response"
        assert isinstance(body[key], expected_type), (
            f"{self.method} {self.url}\n"
            f"  Key '{key}': expected type {expected_type.__name__}, "
            f"got {type(body[key]).__name__} (value: {body[key]!r})"
        )
        return self

    def assert_json_contains(self, subset: dict[str, Any]) -> "APIResponse":
        """Assert every key-value pair in *subset* is present and equal in the response body."""
        body = self.json()
        for key, value in subset.items():
            assert key in body, (
                f"{self.method} {self.url} — key '{key}' missing from body"
            )
            assert body[key] == value, (
                f"{self.method} {self.url}\n"
                f"  Key '{key}': expected {value!r}, got {body[key]!r}"
            )
        return self

    def assert_json_list_length(self, key: str, expected_length: int) -> "APIResponse":
        body = self.json()
        assert key in body, f"Key '{key}' not found in response"
        items = body[key]
        assert isinstance(items, list), (
            f"Key '{key}' is not a list (got {type(items).__name__})"
        )
        assert len(items) == expected_length, (
            f"{self.method} {self.url}\n"
            f"  List '{key}': expected {expected_length} items, got {len(items)}"
        )
        return self

    def assert_json_list_not_empty(self, key: str) -> "APIResponse":
        body = self.json()
        assert key in body, f"Key '{key}' not found in response"
        items = body[key]
        assert isinstance(items, list) and len(items) > 0, (
            f"{self.method} {self.url} — list '{key}' is empty or not a list"
        )
        return self

    def assert_json_list_items_have_keys(self, list_key: str, *keys: str) -> "APIResponse":
        """Assert every item in a top-level JSON array has all *keys*."""
        body = self.json()
        items = body[list_key]
        for idx, item in enumerate(items):
            for key in keys:
                assert key in item, (
                    f"{self.method} {self.url}\n"
                    f"  Item {idx} in '{list_key}' is missing key '{key}'. "
                    f"Present: {list(item.keys())}"
                )
        return self

    def assert_schema(self, required_keys: list[str]) -> "APIResponse":
        """Assert all *required_keys* exist in the top-level JSON object."""
        return self.assert_json_key_exists(*required_keys)

    def assert_json_path(self, path: str, expected: Any) -> "APIResponse":
        """Assert a nested value using dot-separated path, e.g. 'data.email'."""
        body = self.json()
        parts = path.split(".")
        current = body
        for part in parts:
            assert isinstance(current, dict) and part in current, (
                f"{self.method} {self.url} — path '{path}' not found at '{part}'"
            )
            current = current[part]
        assert current == expected, (
            f"{self.method} {self.url}\n"
            f"  Path '{path}': expected {expected!r}, got {current!r}"
        )
        return self

    # ── Header assertions ──────────────────────────────────────────────────────

    def assert_header(self, name: str, expected: str) -> "APIResponse":
        actual = self.headers.get(name.lower())
        assert actual == expected, (
            f"{self.method} {self.url}\n"
            f"  Header '{name}': expected {expected!r}, got {actual!r}"
        )
        return self

    def assert_header_contains(self, name: str, substring: str) -> "APIResponse":
        actual = self.headers.get(name.lower(), "")
        assert substring.lower() in actual.lower(), (
            f"{self.method} {self.url}\n"
            f"  Header '{name}' ({actual!r}) does not contain {substring!r}"
        )
        return self

    def assert_content_type_json(self) -> "APIResponse":
        return self.assert_header_contains("content-type", "application/json")

    # ── Performance assertions ─────────────────────────────────────────────────

    def assert_response_time(self, max_ms: float) -> "APIResponse":
        assert self.elapsed_ms <= max_ms, (
            f"{self.method} {self.url}\n"
            f"  Response too slow: {self.elapsed_ms:.0f}ms > {max_ms:.0f}ms"
        )
        return self

    # ── Data extraction (for request chaining) ─────────────────────────────────

    def extract(self, key: str) -> Any:
        """Extract a top-level JSON value — use the result in the next request."""
        body = self.json()
        assert key in body, (
            f"Cannot extract '{key}' from {self.method} {self.url}. "
            f"Present keys: {list(body.keys())}"
        )
        return body[key]

    def extract_path(self, path: str) -> Any:
        """Extract a nested value using dot-separated path, e.g. 'data.id'."""
        body = self.json()
        parts = path.split(".")
        current = body
        for part in parts:
            assert isinstance(current, dict) and part in current, (
                f"Cannot extract path '{path}' at '{part}'"
            )
            current = current[part]
        return current

    def __repr__(self) -> str:
        return (
            f"APIResponse({self.method} {self.url} → "
            f"HTTP {self.status_code}, {self.elapsed_ms:.0f}ms)"
        )
