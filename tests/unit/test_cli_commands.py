"""
Tests for cli.commands using Click's CliRunner.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.commands import framework


@pytest.fixture
def runner():
    return CliRunner()


# ── --version ────────────────────────────────────────────────────────────────

def test_version_prints_version(runner):
    result = runner.invoke(framework, ["--version"])
    assert result.exit_code == 0
    assert "2.1.0" in result.output


# ── setup --non-interactive ───────────────────────────────────────────────────

def test_setup_non_interactive_creates_env_and_config(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, [
            "setup",
            "--non-interactive",
            "--url", "https://example.com",
            "--name", "testapp",
        ])
        assert result.exit_code == 0, result.output
        assert Path(".env").exists()
        assert Path("config.json").exists()


def test_setup_non_interactive_env_has_base_url(runner):
    with runner.isolated_filesystem():
        runner.invoke(framework, [
            "setup",
            "--non-interactive",
            "--url", "https://myapp.example.com",
            "--name", "myapp",
        ])
        env_content = Path(".env").read_text(encoding="utf-8")
        assert "BASE_URL=https://myapp.example.com" in env_content


def test_setup_non_interactive_config_has_url(runner):
    with runner.isolated_filesystem():
        runner.invoke(framework, [
            "setup",
            "--non-interactive",
            "--url", "https://myapp.example.com",
            "--name", "myapp",
        ])
        cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
        assert cfg["app"]["base_url"] == "https://myapp.example.com"


def test_setup_missing_url_nonzero(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, [
            "setup",
            "--non-interactive",
            "--name", "myapp",
        ])
        assert result.exit_code != 0


def test_setup_missing_name_nonzero(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, [
            "setup",
            "--non-interactive",
            "--url", "https://example.com",
        ])
        assert result.exit_code != 0


# ── add-story ─────────────────────────────────────────────────────────────────

def test_add_story_text_creates_json(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, [
            "add-story",
            "--text", "As a user I want to log in",
        ])
        assert result.exit_code == 0, result.output
        story_files = list(Path("stories").glob("*.json"))
        assert len(story_files) >= 1


def test_add_story_no_args_nonzero(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, ["add-story"])
        assert result.exit_code != 0


def test_add_story_output_dir_created(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, [
            "add-story",
            "--text", "As a user I want to navigate to home page",
            "--output-dir", "custom_stories",
        ])
        assert result.exit_code == 0, result.output
        assert Path("custom_stories").exists()


# ── build --no-probe ──────────────────────────────────────────────────────────

def test_build_no_probe_with_story_file(runner, tmp_path):
    with runner.isolated_filesystem():
        story = {
            "id": "login_001",
            "title": "User Login",
            "description": "Login to the app",
            "actor": "user",
            "tags": ["smoke"],
            "base_url": "https://example.com",
            "steps": [
                {"id": "step_01", "action": "navigate", "target": "/login",
                 "value": "", "description": "Open login page"},
                {"id": "step_02", "action": "fill", "target": "#username",
                 "value": "admin", "description": "Enter username"},
            ],
            "negative_scenarios": [],
        }
        Path("stories").mkdir(exist_ok=True)
        story_file = Path("stories") / "login_001.json"
        story_file.write_text(json.dumps(story), encoding="utf-8")

        result = runner.invoke(framework, [
            "build",
            "--story", str(story_file),
            "--base-url", "https://example.com",
            "--no-probe",
        ])
        assert result.exit_code == 0, result.output
        assert "Build complete" in result.output


# ── fix-selector ──────────────────────────────────────────────────────────────

def test_fix_selector_patches_constant(runner, tmp_path):
    with runner.isolated_filesystem():
        locator_content = 'LOGIN_BUTTON = "#old-selector"\nSOME_OTHER = "#other"\n'
        Path("locators").mkdir(exist_ok=True)
        loc_file = Path("locators") / "test_locators.py"
        loc_file.write_text(locator_content, encoding="utf-8")

        result = runner.invoke(framework, [
            "fix-selector",
            "--file", str(loc_file),
            "--constant", "LOGIN_BUTTON",
            "--selector", "[data-test='login-btn']",
        ])
        assert result.exit_code == 0, result.output
        updated = loc_file.read_text(encoding="utf-8")
        assert "[data-test='login-btn']" in updated
        assert "#old-selector" not in updated


def test_fix_selector_missing_constant_nonzero(runner):
    with runner.isolated_filesystem():
        locator_content = 'SOME_CONSTANT = "#value"\n'
        Path("locators").mkdir(exist_ok=True)
        loc_file = Path("locators") / "test_locators.py"
        loc_file.write_text(locator_content, encoding="utf-8")

        result = runner.invoke(framework, [
            "fix-selector",
            "--file", str(loc_file),
            "--constant", "NONEXISTENT_CONSTANT",
            "--selector", "#new-value",
        ])
        assert result.exit_code != 0


# ── generate-page ─────────────────────────────────────────────────────────────

def test_generate_page_creates_files(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, [
            "generate-page",
            "--url", "https://example.com/login",
        ])
        assert result.exit_code == 0, result.output
        assert Path("pages").exists()
        assert Path("locators").exists()


# ── generate-test ─────────────────────────────────────────────────────────────

def test_generate_test_from_story_file(runner):
    with runner.isolated_filesystem():
        story = {
            "id": "gen_test_001",
            "title": "Generated Test",
            "description": "Test generation",
            "steps": [
                {"id": "step_01", "action": "navigate", "target": "/", "value": "", "description": "Open page"},
            ],
            "tags": ["smoke"],
            "negative_scenarios": [],
        }
        story_file = Path("test_story.json")
        story_file.write_text(json.dumps(story), encoding="utf-8")

        result = runner.invoke(framework, [
            "generate-test",
            "--story", str(story_file),
        ])
        assert result.exit_code == 0, result.output
        test_files = list(Path("tests").glob("**/*.py"))
        assert len(test_files) >= 1


# ── generate-api-test ─────────────────────────────────────────────────────────

def test_generate_api_test_from_story_file(runner):
    with runner.isolated_filesystem():
        story = {
            "id": "api_test_001",
            "title": "API Test",
            "description": "API smoke test",
            "steps": [],
            "tags": ["api"],
            "endpoints": [
                {"id": "root", "method": "GET", "path": "/", "description": "Root", "expected_status": 200}
            ],
            "negative_scenarios": [],
        }
        story_file = Path("api_story.json")
        story_file.write_text(json.dumps(story), encoding="utf-8")

        result = runner.invoke(framework, [
            "generate-api-test",
            "--story", str(story_file),
        ])
        assert result.exit_code == 0, result.output


# ── memory --action show ──────────────────────────────────────────────────────

def test_memory_show_action(runner, tmp_path):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, ["memory", "--action", "show"])
        # Should succeed (may be empty memory engine)
        assert result.exit_code == 0, result.output


def test_memory_search_requires_query(runner):
    with runner.isolated_filesystem():
        result = runner.invoke(framework, ["memory", "--action", "search"])
        assert result.exit_code != 0


# ── fix-selector: injection safety ───────────────────────────────────────────

def test_fix_selector_regex_backref_inserted_literally(runner):
    """A selector containing a regex backref like \\g<0> must be written literally,
    not expanded by the regex substitution engine."""
    with runner.isolated_filesystem():
        locator_content = 'LOGIN_BUTTON = "old"\n'
        Path("locators").mkdir(exist_ok=True)
        loc_file = Path("locators") / "test_locators.py"
        loc_file.write_text(locator_content, encoding="utf-8")

        tricky_selector = r"\g<0>"
        result = runner.invoke(framework, [
            "fix-selector",
            "--file", str(loc_file),
            "--constant", "LOGIN_BUTTON",
            "--selector", tricky_selector,
        ])
        assert result.exit_code == 0, result.output
        updated = loc_file.read_text(encoding="utf-8")
        # The literal string \g<0> must appear in the file, not an expanded group
        assert r"\g<0>" in updated


def test_fix_selector_backref_1_inserted_literally(runner):
    r"""A selector containing \1 must be written literally."""
    with runner.isolated_filesystem():
        locator_content = 'SUBMIT_BTN = "old"\n'
        Path("locators").mkdir(exist_ok=True)
        loc_file = Path("locators") / "test_locators.py"
        loc_file.write_text(locator_content, encoding="utf-8")

        tricky_selector = r"\1"
        result = runner.invoke(framework, [
            "fix-selector",
            "--file", str(loc_file),
            "--constant", "SUBMIT_BTN",
            "--selector", tricky_selector,
        ])
        assert result.exit_code == 0, result.output
        updated = loc_file.read_text(encoding="utf-8")
        assert r"\1" in updated


def test_fix_selector_rejects_selector_with_double_quote(runner):
    """A selector containing a double-quote character must be rejected with a non-zero exit."""
    with runner.isolated_filesystem():
        locator_content = 'LOGIN_BUTTON = "old"\n'
        Path("locators").mkdir(exist_ok=True)
        loc_file = Path("locators") / "test_locators.py"
        loc_file.write_text(locator_content, encoding="utf-8")

        result = runner.invoke(framework, [
            "fix-selector",
            "--file", str(loc_file),
            "--constant", "LOGIN_BUTTON",
            "--selector", 'input[name="user"]',
        ])
        assert result.exit_code != 0


# ── setup: .env sanitization ─────────────────────────────────────────────────

def test_setup_newline_in_username_not_injected(runner):
    """A username containing an embedded newline + extra key must NOT inject a rogue .env line."""
    with runner.isolated_filesystem():
        injected_username = "normaluser\nINJECTED=1"
        result = runner.invoke(framework, [
            "setup",
            "--non-interactive",
            "--url", "https://example.com",
            "--name", "testapp",
            "--username", injected_username,
            "--password", "somepassword",
        ])
        assert result.exit_code == 0, result.output
        env_content = Path(".env").read_text(encoding="utf-8")
        lines = env_content.splitlines()
        # There must be no standalone INJECTED=1 line
        assert "INJECTED=1" not in lines


def test_setup_newline_in_password_not_injected(runner):
    """A password containing an embedded newline must NOT inject a rogue .env line."""
    with runner.isolated_filesystem():
        injected_password = "secret\nINJECTED=evil"
        result = runner.invoke(framework, [
            "setup",
            "--non-interactive",
            "--url", "https://example.com",
            "--name", "testapp",
            "--username", "admin",
            "--password", injected_password,
        ])
        assert result.exit_code == 0, result.output
        env_content = Path(".env").read_text(encoding="utf-8")
        lines = env_content.splitlines()
        assert "INJECTED=evil" not in lines


# ── demo ─────────────────────────────────────────────────────────────────────

class _FakeProcess:
    """Minimal subprocess.CompletedProcess stand-in."""
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


def test_demo_defaults(runner, monkeypatch):
    """demo with no args runs 5 subprocesses using SauceDemo defaults."""
    calls = []

    def fake_run(cmd, env=None, **kwargs):
        calls.append(cmd)
        return _FakeProcess(0)

    monkeypatch.setattr("subprocess.run", fake_run)

    result = runner.invoke(framework, ["demo"])
    assert result.exit_code == 0, result.output
    # Exactly 5 subprocess calls
    assert len(calls) == 5
    # Flatten all args to strings for easy searching
    all_args = [str(a) for c in calls for a in c]
    assert "https://www.saucedemo.com" in all_args
    assert "standard_user" in all_args
    assert "secret_sauce" in all_args


def test_demo_custom_url(runner, monkeypatch):
    """demo --url uses provided values, NOT SauceDemo defaults."""
    calls = []

    def fake_run(cmd, env=None, **kwargs):
        calls.append(cmd)
        return _FakeProcess(0)

    monkeypatch.setattr("subprocess.run", fake_run)

    result = runner.invoke(framework, [
        "demo",
        "--url", "https://myapp.com",
        "--username", "u",
        "--password", "p",
    ])
    assert result.exit_code == 0, result.output
    all_args = [str(a) for c in calls for a in c]
    # Custom values must appear
    assert "https://myapp.com" in all_args
    assert "u" in all_args
    assert "p" in all_args
    # SauceDemo defaults must NOT appear in setup call (second call)
    setup_args = [str(a) for a in calls[1]]
    assert "https://www.saucedemo.com" not in setup_args
    assert "standard_user" not in setup_args
    assert "secret_sauce" not in setup_args


def test_demo_headless_flag(runner, monkeypatch):
    """demo --headless passes --headless to the run step."""
    calls = []

    def fake_run(cmd, env=None, **kwargs):
        calls.append(cmd)
        return _FakeProcess(0)

    monkeypatch.setattr("subprocess.run", fake_run)

    result = runner.invoke(framework, ["demo", "--headless"])
    assert result.exit_code == 0, result.output
    # The 5th call is the run step
    run_cmd = [str(a) for a in calls[4]]
    assert "--headless" in run_cmd


def test_demo_fails_on_step_error(runner, monkeypatch):
    """demo exits with code 1 when a step fails; subsequent steps are not called."""
    calls = []
    call_index = [0]

    def fake_run(cmd, env=None, **kwargs):
        idx = call_index[0]
        call_index[0] += 1
        calls.append(cmd)
        # Fail on the third call (add-story, index 2)
        if idx == 2:
            return _FakeProcess(1)
        return _FakeProcess(0)

    monkeypatch.setattr("subprocess.run", fake_run)

    result = runner.invoke(framework, ["demo"])
    assert result.exit_code == 1
    # Only 3 calls should have been made (clean, setup, add-story); build and run skipped
    assert len(calls) == 3
