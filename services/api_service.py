"""
APIService — production-ready HTTP client for API testing.

Features
  - Returns APIResponse objects with chainable assertions (not raw dicts)
  - Response-time tracking on every request
  - Structured request/response logging
  - Configurable retry with exponential back-off for transient errors
  - Session-level auth: Bearer token, API key header, HTTP Basic
  - Query-string params on GET requests
  - No third-party dependencies — pure stdlib
"""
from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any, Dict, Optional
from urllib import error, request
from urllib.parse import urlencode

from services.api_response import APIResponse

logger = logging.getLogger(__name__)

_RETRYABLE_CODES = {429, 500, 502, 503, 504}


class APIError(Exception):
    """Raised only for network-level failures (no HTTP response received)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class APIService:
    """Synchronous HTTP client that returns APIResponse objects.

    max_retries=0 (default for test clients) means responses are returned as-is
    so tests can assert on 4xx/5xx status codes directly.
    Set max_retries>0 for setup/teardown helpers that need reliability.
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        max_retries: int = 0,
        retry_backoff_base: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._retry_backoff_base = retry_backoff_base
        self._headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            self._headers.update(headers)

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def set_bearer_token(self, token: str) -> None:
        self._headers["Authorization"] = f"Bearer {token}"

    def set_api_key(self, key: str, header_name: str = "X-API-Key") -> None:
        self._headers[header_name] = key

    def set_basic_auth(self, username: str, password: str) -> None:
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._headers["Authorization"] = f"Basic {encoded}"

    def clear_auth(self) -> None:
        self._headers.pop("Authorization", None)

    # ── HTTP verbs ─────────────────────────────────────────────────────────────

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        url = self._build_url(path)
        if params:
            url = f"{url}?{urlencode(params)}"
        return self._execute(url, method="GET")

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self._execute(self._build_url(path), method="POST", body=body)

    def put(self, path: str, body: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self._execute(self._build_url(path), method="PUT", body=body)

    def patch(self, path: str, body: Optional[Dict[str, Any]] = None) -> APIResponse:
        return self._execute(self._build_url(path), method="PATCH", body=body)

    def delete(self, path: str) -> APIResponse:
        return self._execute(self._build_url(path), method="DELETE")

    # ── Domain helpers for test data setup/teardown ───────────────────────────

    def create_test_user(self, email: str, password: str, **extra: Any) -> APIResponse:
        return self.post("/api/users", {"email": email, "password": password, **extra})

    def delete_test_user(self, user_id: str) -> APIResponse:
        return self.delete(f"/api/users/{user_id}")

    def get_auth_token(self, email: str, password: str) -> str:
        """Login and return the raw token string (for injecting into Bearer headers)."""
        resp = self.post("/api/auth/login", {"email": email, "password": password})
        body = resp.json()
        return body.get("token", body.get("access_token", ""))

    # ── Internals ──────────────────────────────────────────────────────────────

    def _build_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        separator = "" if path.startswith("/") else "/"
        return f"{self.base_url}{separator}{path}"

    def _execute(
        self,
        url: str,
        method: str,
        body: Optional[Dict[str, Any]] = None,
        _attempt: int = 0,
    ) -> APIResponse:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = request.Request(url, data=data, headers=self._headers.copy(), method=method)

        logger.debug("→ %s %s", method, url)
        start = time.monotonic()

        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                elapsed_ms = (time.monotonic() - start) * 1000
                raw = resp.read()
                status = resp.status
                headers = dict(resp.headers)
                logger.debug("← %d (%.0fms) %s", status, elapsed_ms, url)
                return APIResponse(
                    status_code=status,
                    body=raw,
                    headers=headers,
                    elapsed_ms=elapsed_ms,
                    url=url,
                    method=method,
                )

        except error.HTTPError as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            # Retry transient server errors if configured
            if exc.code in _RETRYABLE_CODES and _attempt < self.max_retries:
                wait = self._retry_backoff_base * (2 ** _attempt)
                logger.warning(
                    "Retrying %s %s (HTTP %d) in %.1fs [attempt %d/%d]",
                    method, url, exc.code, wait, _attempt + 1, self.max_retries,
                )
                time.sleep(wait)
                return self._execute(url, method, body, _attempt + 1)

            # Return error responses as APIResponse so tests can assert on them
            raw = exc.read()
            headers = dict(exc.headers)
            logger.debug("← %d (%.0fms) %s", exc.code, elapsed_ms, url)
            return APIResponse(
                status_code=exc.code,
                body=raw,
                headers=headers,
                elapsed_ms=elapsed_ms,
                url=url,
                method=method,
            )

        except error.URLError as exc:
            raise APIError(f"Network error reaching {url}: {exc.reason}") from exc
