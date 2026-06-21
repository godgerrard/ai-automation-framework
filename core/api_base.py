"""
APIBase — base class for domain-specific API clients.

Mirrors the role BasePage plays for web Page Objects:
  BasePage → LoginPage → test uses LoginPage
  APIBase  → UsersAPI  → test uses UsersAPI

Usage — create a domain client:

    class UsersAPI(APIBase):
        def list(self, page: int = 1) -> APIResponse:
            return self.get("/api/users", page=page)

        def get_user(self, user_id: int) -> APIResponse:
            return self.get(f"/api/users/{user_id}")

        def create(self, name: str, job: str) -> APIResponse:
            return self.post("/api/users", {"name": name, "job": job})

Then in tests inject via fixture:

    @pytest.fixture(scope="session")
    def users_api(api_client):
        return UsersAPI(api_client)

    def test_create_user(users_api):
        resp = users_api.create("morpheus", "leader")
        resp.assert_created().assert_json_key_exists("id", "createdAt")
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from services.api_service import APIService
from services.api_response import APIResponse

logger = logging.getLogger(__name__)


class APIBase:
    """Base for all domain API client classes."""

    def __init__(self, client: APIService) -> None:
        self._client = client

    # ── HTTP delegates ─────────────────────────────────────────────────────────

    def get(self, path: str, **params: Any) -> APIResponse:
        return self._client.get(path, params=params if params else None)

    def post(self, path: str, body: Optional[dict[str, Any]] = None) -> APIResponse:
        return self._client.post(path, body)

    def put(self, path: str, body: Optional[dict[str, Any]] = None) -> APIResponse:
        return self._client.put(path, body)

    def patch(self, path: str, body: Optional[dict[str, Any]] = None) -> APIResponse:
        return self._client.patch(path, body)

    def delete(self, path: str) -> APIResponse:
        return self._client.delete(path)

    # ── Auth pass-through ──────────────────────────────────────────────────────

    def authenticate(self, token: str) -> None:
        self._client.set_bearer_token(token)
        logger.debug("Bearer token applied to API client")

    def clear_auth(self) -> None:
        self._client.clear_auth()
