"""
Tests for pure private helpers from cli.commands and utils.helpers.
"""
from __future__ import annotations

import pytest

# cli.commands private helpers
from cli.commands import (
    _camel_to_snake,
    _stories_to_env_prefix,
    _story_to_project_name,
    _url_to_class_name,
    _url_to_project_name,
)

# utils.helpers private helpers
from utils.helpers import _action_to_code, _infer_action, _slug, is_safe_probe_url


# ── _url_to_project_name ──────────────────────────────────────────────────────

def test_url_to_project_name_basic():
    assert _url_to_project_name("https://saucedemo.com") == "saucedemo"


def test_url_to_project_name_strips_www():
    assert _url_to_project_name("https://www.example.com") == "example"


def test_url_to_project_name_ignores_path():
    assert _url_to_project_name("https://myapp.com/login") == "myapp"


def test_url_to_project_name_lowercase():
    result = _url_to_project_name("https://MyApp.com")
    assert result == result.lower()


# ── _url_to_class_name ────────────────────────────────────────────────────────

def test_url_to_class_name_from_path_segment():
    result = _url_to_class_name("https://example.com/login")
    assert result == "Login"


def test_url_to_class_name_from_netloc_when_no_path():
    result = _url_to_class_name("https://myapp.com")
    assert result == "Myapp"


def test_url_to_class_name_capitalizes():
    result = _url_to_class_name("https://example.com/user-profile")
    assert result[0].isupper()


def test_url_to_class_name_handles_trailing_slash():
    result = _url_to_class_name("https://example.com/dashboard/")
    # Last non-empty segment is 'dashboard'
    assert "Dashboard" in result


def test_url_to_class_name_default_page():
    result = _url_to_class_name("https://example.com/")
    assert len(result) > 0


# ── _camel_to_snake (cli.commands) ───────────────────────────────────────────

def test_camel_to_snake_basic():
    assert _camel_to_snake("LoginPage") == "login_page"


def test_camel_to_snake_acronym():
    # The regex groups consecutive uppercase as one word: MyHTMLPage -> my_html_page
    assert _camel_to_snake("MyHTMLPage") == "my_html_page"


def test_camel_to_snake_already_snake():
    assert _camel_to_snake("already_snake") == "already_snake"


def test_camel_to_snake_all_lower():
    assert _camel_to_snake("page") == "page"


def test_camel_to_snake_multi_word():
    assert _camel_to_snake("UserProfilePage") == "user_profile_page"


# ── _story_to_project_name ────────────────────────────────────────────────────

def test_story_to_project_name_drops_numeric_suffix():
    result = _story_to_project_name("login_flow_001")
    assert "001" not in result
    assert "login" in result


def test_story_to_project_name_two_parts():
    result = _story_to_project_name("checkout_flow_002")
    assert result == "checkout_flow"


def test_story_to_project_name_no_numeric():
    result = _story_to_project_name("login_flow")
    assert result == "login_flow"


def test_story_to_project_name_single_word():
    result = _story_to_project_name("login")
    assert result == "login"


def test_story_to_project_name_long_id_no_truncation():
    # LOW-5: no arbitrary 2-word cap — all non-numeric parts are preserved
    result = _story_to_project_name("inventory_page_flow_001")
    assert result == "inventory_page_flow"


def test_story_to_project_name_multi_numeric_suffix():
    # Multiple trailing numeric segments should all be stripped
    result = _story_to_project_name("checkout_flow_2_003")
    assert result == "checkout_flow"


# ── _infer_action ─────────────────────────────────────────────────────────────

def test_infer_action_click():
    assert _infer_action("click the login button") == "click"


def test_infer_action_fill():
    assert _infer_action("enter the username in the field") == "fill"


def test_infer_action_navigate():
    assert _infer_action("navigate to the login page") == "navigate"


def test_infer_action_assert_url():
    assert _infer_action("check the URL redirect") == "assert_url"


def test_infer_action_default():
    # unrecognized -> assert_visible
    assert _infer_action("something entirely different") == "assert_visible"


def test_infer_action_press():
    assert _infer_action("press the submit button") == "click"


def test_infer_action_type():
    assert _infer_action("type the password") == "fill"


# ── _action_to_code ───────────────────────────────────────────────────────────

def test_action_to_code_navigate():
    code = _action_to_code("navigate", "/login", "", "")
    assert 'page.goto(' in code
    assert "/login" in code


def test_action_to_code_fill():
    code = _action_to_code("fill", "#username", "admin", "")
    assert 'page.fill(' in code
    assert "admin" in code


def test_action_to_code_click():
    code = _action_to_code("click", "#submit", "", "")
    assert 'page.click(' in code


def test_action_to_code_assert_url():
    code = _action_to_code("assert_url", "/dashboard", "", "")
    assert "wait_for_url" in code


def test_action_to_code_assert_visible():
    code = _action_to_code("assert_visible", "#element", "", "")
    assert "is_visible" in code


def test_action_to_code_includes_comment():
    code = _action_to_code("click", "#btn", "", "Click the button")
    assert "Click the button" in code


def test_action_to_code_unknown_action_fails_loudly():
    # HIGH-2: unknown actions must generate a pytest.fail call, not a silent TODO comment
    code = _action_to_code("unknown_action", "#el", "", "")
    assert "pytest.fail" in code
    assert "unknown_action" in code
    # The generated line must still be valid Python (compiles)
    compile(f"import pytest\n{code}", "<test>", "exec")


# ── _slug ─────────────────────────────────────────────────────────────────────

def test_slug_spaces_to_underscores():
    assert _slug("hello world") == "hello_world"


def test_slug_special_chars_removed():
    result = _slug("hello! world?")
    assert "!" not in result
    assert "?" not in result


def test_slug_lowercase():
    result = _slug("Hello World")
    assert result == result.lower()


def test_slug_strips_underscores():
    result = _slug("  hello  ")
    assert not result.startswith("_")
    assert not result.endswith("_")


# ── _stories_to_env_prefix (MEDIUM-3) ────────────────────────────────────────

def test_stories_to_env_prefix_basic(tmp_path):
    # MEDIUM-3: prefix is derived from the first story file name, uppercased
    f = tmp_path / "myapp_login_001.json"
    f.write_text("{}", encoding="utf-8")
    result = _stories_to_env_prefix([str(f)])
    assert result == "MYAPP_LOGIN"


def test_stories_to_env_prefix_long_name(tmp_path):
    # LOW-5 interaction: long name preserved, not truncated to 2 words
    f = tmp_path / "inventory_page_flow_001.json"
    f.write_text("{}", encoding="utf-8")
    result = _stories_to_env_prefix([str(f)])
    assert result == "INVENTORY_PAGE_FLOW"


def test_stories_to_env_prefix_fallback_no_files():
    # MEDIUM-3: when no story files provided, falls back to 'PROJECT'
    result = _stories_to_env_prefix([])
    assert result == "PROJECT"


def test_stories_to_env_prefix_deterministic(tmp_path):
    # MEDIUM-3: same input always produces same output (no os.environ iteration)
    f = tmp_path / "checkout_flow_002.json"
    f.write_text("{}", encoding="utf-8")
    results = {_stories_to_env_prefix([str(f)]) for _ in range(5)}
    assert len(results) == 1  # always the same value


def test_stories_to_env_prefix_uppercase():
    # env var prefix must be uppercase for correct os.getenv lookup
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix="_login_001.json", delete=False) as f:
        f.write(b"{}")
        fname = f.name
    try:
        result = _stories_to_env_prefix([fname])
        assert result == result.upper()
    finally:
        os.unlink(fname)


# ── is_safe_probe_url ─────────────────────────────────────────────────────────

def test_safe_probe_url_accepts_http_localhost():
    ok, reason = is_safe_probe_url("http://localhost:3000")
    assert ok is True
    assert reason == ""


def test_safe_probe_url_accepts_https_example():
    ok, reason = is_safe_probe_url("https://example.com")
    assert ok is True
    assert reason == ""


def test_safe_probe_url_accepts_http_127_with_path():
    ok, reason = is_safe_probe_url("http://127.0.0.1:8080/path")
    assert ok is True
    assert reason == ""


def test_safe_probe_url_rejects_file_scheme():
    ok, reason = is_safe_probe_url("file:///etc/passwd")
    assert ok is False
    assert reason != ""


def test_safe_probe_url_rejects_javascript_scheme():
    ok, reason = is_safe_probe_url("javascript:alert(1)")
    assert ok is False
    assert reason != ""


def test_safe_probe_url_rejects_data_scheme():
    ok, reason = is_safe_probe_url("data:text/html,x")
    assert ok is False
    assert reason != ""


def test_safe_probe_url_rejects_empty_string():
    ok, reason = is_safe_probe_url("")
    assert ok is False
    assert reason != ""


def test_safe_probe_url_rejects_non_url_string():
    ok, reason = is_safe_probe_url("not a url")
    assert ok is False
    assert reason != ""


def test_safe_probe_url_rejects_overlength():
    long_url = "https://example.com/" + "a" * 2048
    assert len(long_url) > 2048
    ok, reason = is_safe_probe_url(long_url)
    assert ok is False
    assert "2048" in reason


def test_safe_probe_url_rejects_non_string():
    ok, reason = is_safe_probe_url(None)  # type: ignore[arg-type]
    assert ok is False
    assert reason != ""


def test_safe_probe_url_rejects_ftp_scheme():
    ok, reason = is_safe_probe_url("ftp://files.example.com/pub")
    assert ok is False
    assert reason != ""


def test_safe_probe_url_rejects_no_netloc():
    ok, reason = is_safe_probe_url("http://")
    assert ok is False
    assert reason != ""
