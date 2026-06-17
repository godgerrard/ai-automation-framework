"""
APIService — thin urllib wrapper for test data setup and teardown.

Avoids the `requests` dependency so the framework stays lean.
URL construction uses explicit string concatenation (not urljoin) to guarantee
correct behaviour regardless of whether the base URL has a path component.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
from urllib import error, request

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class APIService:
    """Synchronous HTTP client for backend test data management."""

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if headers:
            self._headers.update(headers)

    def set_auth_token(self, token: str) -> None:
        self._headers["Authorization"] = f"Bearer {token}"

    # ── HTTP verbs ────────────────────────────────────────────────────────────

    def get(self, path: str) -> Dict[str, Any]:
        return self._execute(self._build(path, method="GET"))

    def post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute(self._build(path, method="POST", body=body))

    def put(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute(self._build(path, method="PUT", body=body))

    def patch(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute(self._build(path, method="PATCH", body=body))

    def delete(self, path: str) -> Dict[str, Any]:
        return self._execute(self._build(path, method="DELETE"))

    # ── Domain helpers ────────────────────────────────────────────────────────

    def create_test_user(self, email: str, password: str, **extra: Any) -> Dict[str, Any]:
        return self.post("/api/users", {"email": email, "password": password, **extra})

    def delete_test_user(self, user_id: str) -> Dict[str, Any]:
        return self.delete(f"/api/users/{user_id}")

    def get_auth_token(self, email: str, password: str) -> str:
        resp = self.post("/api/auth/login", {"email": email, "password": password})
        return resp.get("token", resp.get("access_token", ""))

    # ── Internals ─────────────────────────────────────────────────────────────

    def _build_url(self, path: str) -> str:
        """Concatenate base_url and path safely regardless of path format."""
        if path.startswith(("http://", "https://")):
            return path
        separator = "" if path.startswith("/") else "/"
        return f"{self.base_url}{separator}{path}"

    def _build(
        self,
        path: str,
        method: str = "GET",
        body: Optional[Dict[str, Any]] = None,
    ) -> request.Request:
        url = self._build_url(path)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        return request.Request(url, data=data, headers=self._headers, method=method)

    def _execute(self, req: request.Request) -> Dict[str, Any]:
        logger.debug("%s %s", req.get_method(), req.full_url)
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise APIError(exc.code, body) from exc
        except error.URLError as exc:
            raise APIError(0, str(exc.reason)) from exc
