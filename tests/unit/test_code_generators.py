"""
Tests for CodeGenerator, AllureTestGenerator, APICodeGenerator.
"""
from __future__ import annotations

import pytest

from utils.helpers import APICodeGenerator, AllureTestGenerator, CodeGenerator


@pytest.fixture
def gen():
    return CodeGenerator()


@pytest.fixture
def allure_gen():
    return AllureTestGenerator()


@pytest.fixture
def api_gen():
    return APICodeGenerator()


@pytest.fixture
def sample_story():
    return {
        "id": "login_flow_001",
        "title": "User Login",
        "description": "Verify the login flow",
        "actor": "user",
        "tags": ["smoke", "authentication"],
        "steps": [
            {"id": "step_01", "action": "navigate", "target": "/login", "value": "", "description": "Open login page"},
            {"id": "step_02", "action": "fill", "target": "#username", "value": "admin", "description": "Enter username"},
            {"id": "step_03", "action": "click", "target": "#submit", "value": "", "description": "Click login"},
            {"id": "step_04", "action": "assert_url", "target": "/dashboard", "value": "", "description": "Verify redirect"},
        ],
        "negative_scenarios": [
            {"id": "neg_01", "title": "Invalid credentials show error", "expected": "Error shown"},
        ],
    }


@pytest.fixture
def sample_api_story():
    return {
        "id": "api_test_001",
        "title": "API Health Check",
        "description": "Verify API endpoints",
        "tags": ["api", "smoke"],
        "base_url": "https://api.example.com",
        "endpoints": [
            {
                "id": "get_root",
                "method": "GET",
                "path": "/",
                "description": "Root returns 200",
                "expected_status": 200,
                "expected_schema": ["status"],
            }
        ],
        "negative_scenarios": [
            {
                "id": "neg_01",
                "title": "Missing token returns 401",
                "method": "GET",
                "path": "/protected",
                "expected_status": 401,
                "expected": "Unauthorized",
            }
        ],
    }


# ── CodeGenerator.generate_page_class ────────────────────────────────────────

def test_generate_page_class_compiles(gen):
    src = gen.generate_page_class("LoginPage", "https://example.com/login")
    compile(src, "<test>", "exec")


def test_generate_page_class_contains_class_def(gen):
    src = gen.generate_page_class("LoginPage", "https://example.com/login")
    assert "class LoginPage" in src


def test_generate_page_class_imports_base_page(gen):
    src = gen.generate_page_class("LoginPage", "https://example.com/login")
    assert "BasePage" in src


def test_generate_page_class_has_url_path(gen):
    src = gen.generate_page_class("LoginPage", "https://example.com/login")
    assert "URL_PATH" in src


# ── CodeGenerator.generate_locator_class ─────────────────────────────────────

def test_generate_locator_class_compiles(gen):
    src = gen.generate_locator_class("LoginPage")
    compile(src, "<test>", "exec")


def test_generate_locator_class_contains_class(gen):
    src = gen.generate_locator_class("LoginPage")
    assert "class LoginPageLocators" in src


def test_generate_locator_class_has_selectors(gen):
    src = gen.generate_locator_class("LoginPage")
    assert "PAGE_INDICATOR" in src
    assert "PRIMARY_ACTION" in src


# ── CodeGenerator.generate_test_class ────────────────────────────────────────

def test_generate_test_class_compiles(gen, sample_story):
    src = gen.generate_test_class(sample_story)
    compile(src, "<test>", "exec")


def test_generate_test_class_has_class_def(gen, sample_story):
    src = gen.generate_test_class(sample_story)
    assert "class Test" in src


def test_generate_test_class_has_happy_path(gen, sample_story):
    src = gen.generate_test_class(sample_story)
    assert "test_happy_path" in src


def test_generate_test_class_has_pytest_marks(gen, sample_story):
    src = gen.generate_test_class(sample_story)
    assert "@pytest.mark.smoke" in src
    assert "@pytest.mark.authentication" in src


def test_generate_test_class_has_negative_scenario(gen, sample_story):
    src = gen.generate_test_class(sample_story)
    assert "invalid_credentials_show_error" in src


def test_generate_test_class_imports_pytest(gen, sample_story):
    src = gen.generate_test_class(sample_story)
    assert "import pytest" in src


# ── AllureTestGenerator.generate ─────────────────────────────────────────────

def test_allure_generate_compiles(allure_gen, sample_story):
    src = allure_gen.generate(sample_story, "login_flow")
    compile(src, "<test>", "exec")


def test_allure_generate_has_allure_feature(allure_gen, sample_story):
    src = allure_gen.generate(sample_story, "login_flow")
    assert "@allure.feature(" in src


def test_allure_generate_has_allure_severity(allure_gen, sample_story):
    src = allure_gen.generate(sample_story, "login_flow")
    assert "@allure.severity(" in src


def test_allure_generate_has_class_def(allure_gen, sample_story):
    src = allure_gen.generate(sample_story, "login_flow")
    assert "class Test" in src


def test_allure_generate_has_happy_path(allure_gen, sample_story):
    src = allure_gen.generate(sample_story, "login_flow")
    assert "test_happy_path" in src


def test_allure_generate_has_pytest_marks(allure_gen, sample_story):
    src = allure_gen.generate(sample_story, "login_flow")
    assert "@pytest.mark.smoke" in src


# ── APICodeGenerator.generate_test_class ─────────────────────────────────────

def test_api_generate_test_class_compiles(api_gen, sample_api_story):
    src = api_gen.generate_test_class(sample_api_story)
    compile(src, "<test>", "exec")


def test_api_generate_has_class_def(api_gen, sample_api_story):
    src = api_gen.generate_test_class(sample_api_story)
    assert "class Test" in src


def test_api_generate_has_api_import(api_gen, sample_api_story):
    src = api_gen.generate_test_class(sample_api_story)
    assert "APIService" in src


def test_api_generate_has_endpoint_test(api_gen, sample_api_story):
    src = api_gen.generate_test_class(sample_api_story)
    assert "test_get_root" in src


def test_api_generate_has_assert_status(api_gen, sample_api_story):
    src = api_gen.generate_test_class(sample_api_story)
    assert "assert_status(200)" in src


def test_api_generate_has_negative_test(api_gen, sample_api_story):
    src = api_gen.generate_test_class(sample_api_story)
    assert "401" in src


# ── HIGH-2: unknown action generates loud failure, not silent TODO ────────────

def test_codegen_unknown_action_fails_loudly(gen):
    """CodeGenerator must emit pytest.fail for unknown actions — no silent TODO."""
    story = {
        "id": "test_001",
        "title": "Test",
        "description": "",
        "steps": [
            {"id": "step_01", "action": "hover", "target": "#el", "value": "", "description": "Hover over element"},
        ],
        "tags": [],
        "negative_scenarios": [],
    }
    src = gen.generate_test_class(story)
    assert "pytest.fail" in src
    assert "hover" in src
    compile(src, "<test>", "exec")  # must still compile


def test_allure_unknown_action_fails_loudly(allure_gen):
    """AllureTestGenerator must emit pytest.fail for unknown actions."""
    story = {
        "id": "test_001",
        "title": "Test",
        "description": "",
        "actor": "user",
        "steps": [
            {"id": "step_01", "action": "drag", "target": "#source", "value": "#target", "description": "Drag element"},
        ],
        "tags": [],
        "negative_scenarios": [],
    }
    src = allure_gen.generate(story, "test")
    assert "pytest.fail" in src
    assert "drag" in src
    compile(src, "<test>", "exec")  # must still compile


def test_codegen_unknown_action_no_silent_pass(gen):
    """Regression: generated code for unknown action must not be a comment-only line."""
    story = {
        "id": "test_001",
        "title": "Test",
        "description": "",
        "steps": [
            {"id": "step_01", "action": "scroll", "target": "#el", "value": "", "description": "Scroll down"},
        ],
        "tags": [],
        "negative_scenarios": [],
    }
    src = gen.generate_test_class(story)
    # The generated step must NOT be just a comment (starts with #)
    for line in src.splitlines():
        stripped = line.strip()
        if "scroll" in stripped.lower() and stripped.startswith("#"):
            raise AssertionError(f"Unknown action generated as silent comment: {line!r}")
