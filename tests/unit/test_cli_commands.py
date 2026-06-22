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
