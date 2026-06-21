"""
API test fixtures.

Two clients:
  reqres_client  → https://jsonplaceholder.typicode.com (or --api-url override)
                   Used for CRUD / schema / performance tests.
  httpbin_client → https://httpbin.org
                   Used for auth-header capability tests (echoes request headers).

Neither client retries — API tests must see raw status codes.
"""
from __future__ import annotations

import pytest

from services.api_service import APIService


@pytest.fixture(scope="session")
def reqres_client(request: pytest.FixtureRequest) -> APIService:
    """APIService pointed at --api-url (default: jsonplaceholder.typicode.com). No retries."""
    url = request.config.getoption("--api-url")
    return APIService(url, max_retries=0)


@pytest.fixture(scope="session")
def httpbin_client() -> APIService:
    """APIService pointed at httpbin.org — used for auth-header capability tests."""
    return APIService("https://httpbin.org", max_retries=0)
