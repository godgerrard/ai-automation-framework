"""
Tests for StoryParser.
"""
from __future__ import annotations

import json

import pytest

from utils.helpers import StoryParser


@pytest.fixture
def parser():
    return StoryParser()


# ── JSON parsing ──────────────────────────────────────────────────────────────

def test_valid_json_story(parser, tmp_path):
    story = {
        "id": "login_001",
        "title": "User Login",
        "steps": [
            {"id": "step_01", "action": "navigate", "target": "/login", "description": "Open login"}
        ],
    }
    p = tmp_path / "story.json"
    p.write_text(json.dumps(story), encoding="utf-8")
    result = parser.parse_story_file(str(p))
    assert result["id"] == "login_001"
    assert result["title"] == "User Login"
    assert len(result["steps"]) == 1


def test_missing_required_field_raises_value_error(parser, tmp_path):
    # Missing 'steps'
    story = {"id": "login_001", "title": "User Login"}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(story), encoding="utf-8")
    with pytest.raises(ValueError, match="steps"):
        parser.parse_story_file(str(p))


def test_missing_id_raises_value_error(parser, tmp_path):
    story = {"title": "User Login", "steps": []}
    p = tmp_path / "noid.json"
    p.write_text(json.dumps(story), encoding="utf-8")
    with pytest.raises(ValueError):
        parser.parse_story_file(str(p))


def test_missing_title_raises_value_error(parser, tmp_path):
    story = {"id": "s1", "steps": []}
    p = tmp_path / "notitle.json"
    p.write_text(json.dumps(story), encoding="utf-8")
    with pytest.raises(ValueError):
        parser.parse_story_file(str(p))


# ── Text/Markdown parsing ─────────────────────────────────────────────────────

def test_txt_file_parse(parser, tmp_path):
    content = "User Login Test\nGiven I open the login page\nWhen I enter my credentials\nThen I see the dashboard"
    p = tmp_path / "story.txt"
    p.write_text(content, encoding="utf-8")
    result = parser.parse_story_file(str(p))
    assert result["id"] == "story"
    assert result["title"] == "User Login Test"
    assert len(result["steps"]) >= 1


def test_md_file_parse(parser, tmp_path):
    content = "Login Feature\nGiven I am on the page\nWhen I click login\nThen I see dashboard"
    p = tmp_path / "story.md"
    p.write_text(content, encoding="utf-8")
    result = parser.parse_story_file(str(p))
    assert result["id"] == "story"
    assert "steps" in result


def test_unsupported_suffix_raises_value_error(parser, tmp_path):
    p = tmp_path / "story.yaml"
    p.write_text("id: test", encoding="utf-8")
    with pytest.raises(ValueError, match=".yaml"):
        parser.parse_story_file(str(p))


def test_missing_file_raises_file_not_found(parser, tmp_path):
    with pytest.raises(FileNotFoundError):
        parser.parse_story_file(str(tmp_path / "nonexistent.json"))


def test_txt_parse_returns_required_keys(parser, tmp_path):
    content = "My Story\nGiven something happens"
    p = tmp_path / "test.txt"
    p.write_text(content, encoding="utf-8")
    result = parser.parse_story_file(str(p))
    for key in ("id", "title", "steps"):
        assert key in result
