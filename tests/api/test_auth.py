"""
Test suite: Auth header capability tests

Target : https://httpbin.org
         /headers   — echoes every request header back as JSON
         /bearer    — returns 401 without Authorization, 200 with a valid Bearer token
         /basic-auth/user/pass — validates HTTP Basic auth

These tests verify that APIService correctly attaches and clears auth headers.
They are NOT testing a real authentication system — they prove the framework's
auth layer works end-to-end so you can rely on it when pointing at a real API.
"""
from __future__ import annotations

import pytest

from services.api_service import APIService

RESPONSE_TIME_LIMIT_MS = 4000
_TEST_TOKEN = "framework-test-token-abc123"


@pytest.mark.api
class TestAuthCapabilities:
    """Verify APIService auth methods produce correct Authorization headers."""

    # ── Bearer token ──────────────────────────────────────────────────────────

    @pytest.mark.smoke
    def test_bearer_token_appears_in_request_headers(self, httpbin_client: APIService) -> None:
        """Set a Bearer token and confirm the server receives it."""
        httpbin_client.set_bearer_token(_TEST_TOKEN)
        try:
            resp = httpbin_client.get("/headers")
            resp.assert_ok()
            received = resp.json()["headers"]
            assert received.get("Authorization") == f"Bearer {_TEST_TOKEN}", (
                f"Expected 'Bearer {_TEST_TOKEN}', got {received.get('Authorization')!r}"
            )
        finally:
            httpbin_client.clear_auth()

    def test_bearer_endpoint_returns_401_without_token(self, httpbin_client: APIService) -> None:
        httpbin_client.clear_auth()
        resp = httpbin_client.get("/bearer")
        resp.assert_unauthorized()

    def test_bearer_endpoint_returns_200_with_valid_token(self, httpbin_client: APIService) -> None:
        httpbin_client.set_bearer_token(_TEST_TOKEN)
        try:
            resp = httpbin_client.get("/bearer")
            resp.assert_ok()
        finally:
            httpbin_client.clear_auth()

    def test_bearer_response_shows_authenticated_true(self, httpbin_client: APIService) -> None:
        httpbin_client.set_bearer_token(_TEST_TOKEN)
        try:
            resp = httpbin_client.get("/bearer")
            resp.assert_ok().assert_json_key("authenticated", True)
        finally:
            httpbin_client.clear_auth()

    def test_bearer_response_echoes_token(self, httpbin_client: APIService) -> None:
        httpbin_client.set_bearer_token(_TEST_TOKEN)
        try:
            resp = httpbin_client.get("/bearer")
            resp.assert_ok().assert_json_key("token", _TEST_TOKEN)
        finally:
            httpbin_client.clear_auth()

    def test_clear_auth_removes_authorization_header(self, httpbin_client: APIService) -> None:
        """Verify clear_auth() actually removes the Authorization header."""
        httpbin_client.set_bearer_token(_TEST_TOKEN)
        httpbin_client.clear_auth()
        resp = httpbin_client.get("/headers")
        resp.assert_ok()
        received = resp.json()["headers"]
        assert "Authorization" not in received, (
            f"Authorization header should be absent after clear_auth(), found: {received.get('Authorization')!r}"
        )

    # ── Basic auth ────────────────────────────────────────────────────────────

    def test_basic_auth_returns_200_with_correct_credentials(self, httpbin_client: APIService) -> None:
        httpbin_client.set_basic_auth("testuser", "testpass")
        try:
            resp = httpbin_client.get("/basic-auth/testuser/testpass")
            resp.assert_ok()
        finally:
            httpbin_client.clear_auth()

    def test_basic_auth_returns_401_with_wrong_credentials(self, httpbin_client: APIService) -> None:
        httpbin_client.set_basic_auth("testuser", "wrongpassword")
        try:
            resp = httpbin_client.get("/basic-auth/testuser/testpass")
            resp.assert_unauthorized()
        finally:
            httpbin_client.clear_auth()

    def test_basic_auth_response_confirms_authenticated(self, httpbin_client: APIService) -> None:
        httpbin_client.set_basic_auth("alice", "secret")
        try:
            resp = httpbin_client.get("/basic-auth/alice/secret")
            resp.assert_ok().assert_json_key("authenticated", True)
        finally:
            httpbin_client.clear_auth()

    # ── API key header ────────────────────────────────────────────────────────

    def test_api_key_appears_in_request_headers(self, httpbin_client: APIService) -> None:
        """Set an API key header and confirm the server receives it."""
        httpbin_client.set_api_key("my-api-key-xyz", header_name="X-API-Key")
        try:
            resp = httpbin_client.get("/headers")
            resp.assert_ok()
            received = resp.json()["headers"]
            assert received.get("X-Api-Key") == "my-api-key-xyz", (
                f"Expected X-API-Key header, got: {received!r}"
            )
        finally:
            httpbin_client.clear_auth()

    # ── POST with auth ────────────────────────────────────────────────────────

    def test_post_request_sends_bearer_token(self, httpbin_client: APIService) -> None:
        """Bearer token should be present on POST requests too."""
        httpbin_client.set_bearer_token(_TEST_TOKEN)
        try:
            resp = httpbin_client.post("/post", {"field": "value"})
            resp.assert_ok()
            received_headers = resp.json().get("headers", {})
            assert received_headers.get("Authorization") == f"Bearer {_TEST_TOKEN}"
        finally:
            httpbin_client.clear_auth()

    # ── Response time ─────────────────────────────────────────────────────────

    @pytest.mark.smoke
    def test_auth_endpoint_response_time(self, httpbin_client: APIService) -> None:
        httpbin_client.set_bearer_token(_TEST_TOKEN)
        try:
            resp = httpbin_client.get("/bearer")
            resp.assert_ok().assert_response_time(RESPONSE_TIME_LIMIT_MS)
        finally:
            httpbin_client.clear_auth()
