"""
Tests for NaturalLanguageStoryParser.
"""
from __future__ import annotations

import pytest

from utils.helpers import NaturalLanguageStoryParser


@pytest.fixture
def parser():
    return NaturalLanguageStoryParser()


# ── basic happy path ──────────────────────────────────────────────────────────

def test_plain_english_returns_story(parser):
    stories = parser.parse("As a user I want to log in and see the dashboard")
    assert len(stories) >= 1
    s = stories[0]
    assert "id" in s
    assert "title" in s
    assert "steps" in s
    assert isinstance(s["steps"], list)


def test_login_compound_expands_to_four_steps(parser):
    stories = parser.parse("As a user I want to log in")
    steps = stories[0]["steps"]
    # login compound -> fill username, fill password, click button, assert_url
    login_expanded = [
        s for s in steps
        if s["action"] in ("fill", "click", "assert_url")
    ]
    assert len(login_expanded) >= 4


def test_login_step_actions(parser):
    stories = parser.parse("As a user I want to log in")
    steps = stories[0]["steps"]
    actions = [s["action"] for s in steps]
    assert "fill" in actions
    assert "click" in actions
    assert "assert_url" in actions


def test_logout_expands_to_two_steps(parser):
    stories = parser.parse("As a user I want to log out")
    steps = stories[0]["steps"]
    logout_steps = [s for s in steps if s["action"] in ("click", "assert_url")]
    assert len(logout_steps) >= 2


def test_multi_story_split_on_separator(parser):
    text = "As a user I want to log in\n---\nAs a user I want to check out"
    stories = parser.parse(text)
    assert len(stories) == 2


def test_gherkin_given_when_then(parser):
    text = (
        "As a user I want to test the login form\n"
        "Given I am on the login page\n"
        "When I fill in my username\n"
        "Then I should see the dashboard"
    )
    stories = parser.parse(text)
    assert len(stories) >= 1
    steps = stories[0]["steps"]
    assert len(steps) >= 1


def test_tag_inference_authentication(parser):
    stories = parser.parse("As a user I want to log in with my password")
    tags = stories[0]["tags"]
    assert "authentication" in tags


def test_tag_inference_checkout(parser):
    stories = parser.parse("As a buyer I want to checkout my cart and pay")
    tags = stories[0]["tags"]
    assert "checkout" in tags


def test_tag_inference_api(parser):
    stories = parser.parse("Test the REST API endpoint response JSON")
    tags = stories[0]["tags"]
    assert "api" in tags


def test_smoke_tag_always_present(parser):
    stories = parser.parse("As a user I want to see the home page")
    tags = stories[0]["tags"]
    assert "smoke" in tags


def test_negative_extraction(parser):
    text = (
        "As a user I want to log in\n"
        "Negative: invalid credentials should show error\n"
    )
    stories = parser.parse(text)
    negs = stories[0]["negative_scenarios"]
    assert len(negs) >= 1
    assert "id" in negs[0]
    assert "title" in negs[0]


def test_make_id_format(parser):
    stories = parser.parse("As a user I want to navigate to dashboard")
    story_id = stories[0]["id"]
    # id should end with _001 (or _NNN) and be lowercase with underscores
    assert "_" in story_id
    parts = story_id.split("_")
    assert parts[-1].isdigit()


def test_empty_input_returns_empty_list(parser):
    result = parser.parse("")
    assert result == []


def test_empty_whitespace_returns_empty_list(parser):
    result = parser.parse("   \n\n   ")
    assert result == []


def test_parse_returns_list(parser):
    result = parser.parse("As a user I want to see the home page")
    assert isinstance(result, list)


def test_story_has_required_keys(parser):
    stories = parser.parse("As a user I want to do something")
    s = stories[0]
    for key in ("id", "title", "description", "steps", "tags", "negative_scenarios"):
        assert key in s, f"Missing key: {key}"


def test_steps_have_required_keys(parser):
    stories = parser.parse("As a user I want to navigate to login")
    for step in stories[0]["steps"]:
        for key in ("id", "action", "target", "description"):
            assert key in step, f"Step missing key: {key}"
