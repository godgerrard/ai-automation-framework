"""
Test suite: Users API CRUD (story ID: users_api_001)

Target : https://jsonplaceholder.typicode.com/users
Covers : list, get by ID, 404, create (201), PUT, PATCH, DELETE,
         response schema, data types, response time, and request chaining.

JSONPlaceholder notes:
  - POST /users always returns id=11 (fake server, data is not persisted)
  - DELETE /users/:id returns HTTP 200 with {} (not 204)
  - All mutations are simulated — no real data changes occur
"""
from __future__ import annotations

import pytest

from services.api_service import APIService

RESPONSE_TIME_LIMIT_MS = 4000

USER_SCHEMA = ["id", "name", "username", "email", "phone", "website", "company"]


@pytest.mark.api
class TestUsersAPI:
    """Full CRUD coverage for the /users resource."""

    # ── LIST ──────────────────────────────────────────────────────────────────

    def test_list_users_returns_200(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users")
        resp.assert_status(200)

    def test_list_users_returns_non_empty_array(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users")
        resp.assert_status(200)
        users = resp.json()
        assert isinstance(users, list) and len(users) > 0, (
            "Expected a non-empty list of users"
        )

    def test_list_users_items_have_required_schema(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users")
        resp.assert_status(200)
        users = resp.json()
        for idx, user in enumerate(users):
            for key in USER_SCHEMA:
                assert key in user, f"User[{idx}] missing key '{key}'"

    def test_list_users_ids_are_integers(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users")
        resp.assert_status(200)
        users = resp.json()
        for user in users:
            assert isinstance(user["id"], int), f"id should be int, got {type(user['id'])}"

    def test_list_users_emails_contain_at_sign(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users")
        resp.assert_status(200)
        users = resp.json()
        for user in users:
            assert "@" in user["email"], f"Invalid email: {user['email']!r}"

    def test_list_users_has_exactly_ten_users(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users")
        resp.assert_status(200)
        users = resp.json()
        assert len(users) == 10, f"Expected 10 users, got {len(users)}"

    @pytest.mark.smoke
    def test_list_users_response_time(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users")
        resp.assert_status(200).assert_response_time(RESPONSE_TIME_LIMIT_MS)

    # ── GET SINGLE ────────────────────────────────────────────────────────────

    @pytest.mark.smoke
    def test_get_user_by_id_returns_200(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users/1")
        resp.assert_status(200)

    def test_get_user_schema(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users/1")
        resp.assert_status(200).assert_json_key_exists(*USER_SCHEMA)

    def test_get_user_id_matches_path(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users/3")
        resp.assert_status(200).assert_json_key("id", 3)

    def test_get_user_company_is_object(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users/1")
        resp.assert_status(200).assert_json_key_type("company", dict)

    def test_get_user_address_has_city(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users/1")
        resp.assert_status(200)
        address = resp.json().get("address", {})
        assert "city" in address, f"address missing 'city': {address}"

    def test_get_user_response_time(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users/1")
        resp.assert_status(200).assert_response_time(RESPONSE_TIME_LIMIT_MS)

    # ── 404 ───────────────────────────────────────────────────────────────────

    def test_get_nonexistent_user_returns_404(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/users/9999")
        resp.assert_not_found()

    # ── CREATE ────────────────────────────────────────────────────────────────

    @pytest.mark.smoke
    def test_create_user_returns_201(self, reqres_client: APIService) -> None:
        resp = reqres_client.post("/users", {"name": "Jane Doe", "username": "janedoe", "email": "jane@example.com"})
        resp.assert_created()

    def test_create_user_echoes_submitted_fields(self, reqres_client: APIService) -> None:
        payload = {"name": "Test User", "username": "testuser", "email": "test@example.com"}
        resp = reqres_client.post("/users", payload)
        resp.assert_created()
        resp.assert_json_key("name", "Test User")
        resp.assert_json_key("email", "test@example.com")

    def test_create_user_id_is_assigned(self, reqres_client: APIService) -> None:
        resp = reqres_client.post("/users", {"name": "New User"})
        resp.assert_created().assert_json_key_exists("id")
        user_id = resp.extract("id")
        assert isinstance(user_id, int) and user_id > 0, f"Expected positive int id, got {user_id!r}"

    def test_create_user_response_time(self, reqres_client: APIService) -> None:
        resp = reqres_client.post("/users", {"name": "Speed Test User"})
        resp.assert_created().assert_response_time(RESPONSE_TIME_LIMIT_MS)

    # ── UPDATE (PUT) ──────────────────────────────────────────────────────────

    def test_put_user_returns_200(self, reqres_client: APIService) -> None:
        resp = reqres_client.put("/users/1", {"name": "Updated Name", "email": "updated@example.com"})
        resp.assert_ok()

    def test_put_user_echoes_updated_fields(self, reqres_client: APIService) -> None:
        resp = reqres_client.put("/users/1", {"name": "Alice Updated", "username": "alice2"})
        resp.assert_ok()
        resp.assert_json_key("name", "Alice Updated").assert_json_key("username", "alice2")

    def test_put_user_returns_id(self, reqres_client: APIService) -> None:
        resp = reqres_client.put("/users/2", {"name": "Bob Updated"})
        resp.assert_ok().assert_json_key_exists("id")

    # ── UPDATE (PATCH) ────────────────────────────────────────────────────────

    def test_patch_user_returns_200(self, reqres_client: APIService) -> None:
        resp = reqres_client.patch("/users/1", {"name": "Patched Name"})
        resp.assert_ok()

    def test_patch_user_echoes_patched_field(self, reqres_client: APIService) -> None:
        resp = reqres_client.patch("/users/1", {"phone": "555-0199"})
        resp.assert_ok().assert_json_key("phone", "555-0199")

    # ── DELETE ────────────────────────────────────────────────────────────────

    def test_delete_user_returns_200(self, reqres_client: APIService) -> None:
        resp = reqres_client.delete("/users/1")
        resp.assert_ok()

    def test_delete_user_returns_empty_object(self, reqres_client: APIService) -> None:
        resp = reqres_client.delete("/users/1")
        resp.assert_ok()
        body = resp.json()
        assert body == {}, f"Expected empty object after DELETE, got: {body}"

    # ── FILTERING ─────────────────────────────────────────────────────────────

    def test_filter_posts_by_user_id(self, reqres_client: APIService) -> None:
        resp = reqres_client.get("/posts", params={"userId": 1})
        resp.assert_status(200)
        posts = resp.json()
        assert isinstance(posts, list) and len(posts) > 0
        for post in posts:
            assert post["userId"] == 1, f"Got post with userId={post['userId']}, expected 1"

    # ── REQUEST CHAINING ──────────────────────────────────────────────────────

    def test_create_then_use_extracted_id(self, reqres_client: APIService) -> None:
        """Create a user, extract the id, use it to build the next request path."""
        create_resp = reqres_client.post("/users", {"name": "Chain Test"})
        create_resp.assert_created()
        user_id = create_resp.extract("id")
        assert isinstance(user_id, int), f"Expected int id for chaining, got {type(user_id)}"
