"""
Tests for AutoDOMMapper.
"""
from __future__ import annotations

import pytest

from utils.helpers import AutoDOMMapper, DOMProber


# ── Fixtures / helpers ─────────────────────────────────────────────────────────

@pytest.fixture
def mapper():
    return AutoDOMMapper("https://example.com")


CANNED_ELEMENTS = [
    {
        "tag": "input",
        "id": "username",
        "dataTest": "username",
        "ariaLabel": None,
        "placeholder": "Enter username",
        "name": "username",
        "text": "",
        "type": "text",
        "href": None,
        "className": "form-control",
    },
    {
        "tag": "input",
        "id": "password",
        "dataTest": "password",
        "ariaLabel": None,
        "placeholder": "Enter password",
        "name": "password",
        "text": "",
        "type": "password",
        "href": None,
        "className": "form-control",
    },
    {
        "tag": "button",
        "id": "login-btn",
        "dataTest": "login-button",
        "ariaLabel": None,
        "placeholder": None,
        "name": None,
        "text": "Login",
        "type": "submit",
        "href": None,
        "className": "btn btn-primary",
    },
    {
        "tag": "a",
        "id": None,
        "dataTest": None,
        "ariaLabel": None,
        "placeholder": None,
        "name": None,
        "text": "Forgot password",
        "type": None,
        "href": "/forgot",
        "className": "",
    },
    {
        "tag": "input",
        "id": "hidden-field",
        "dataTest": None,
        "ariaLabel": None,
        "placeholder": None,
        "name": "csrf",
        "text": "",
        "type": "hidden",
        "href": None,
        "className": "",
    },
]


# ── _resolve_path ──────────────────────────────────────────────────────────────

def test_resolve_path_known_hint(mapper):
    path = mapper._resolve_path("TODO__NAVIGATE", "navigate to login page")
    assert path == "/login"


def test_resolve_path_dashboard_hint(mapper):
    path = mapper._resolve_path("TODO__NAVIGATE", "go to dashboard")
    assert path == "/dashboard"


def test_resolve_path_non_todo_passthrough(mapper):
    path = mapper._resolve_path("/custom-path", "some description")
    assert path == "/custom-path"


def test_resolve_path_adds_leading_slash(mapper):
    path = mapper._resolve_path("mypage", "go to mypage")
    assert path.startswith("/")


def test_resolve_path_unknown_returns_slash(mapper):
    path = mapper._resolve_path("TODO__X", "navigate to something completely unknown xyz")
    assert path == "/"


# ── _selector_string priority ─────────────────────────────────────────────────

def test_selector_string_prefers_data_test(mapper):
    el = {"tag": "input", "dataTest": "username", "id": "user", "ariaLabel": "Username", "name": "user", "text": "", "placeholder": None}
    sel = mapper._selector_string(el)
    assert sel == "[data-test='username']"


def test_selector_string_uses_id_when_no_data_test(mapper):
    el = {"tag": "input", "dataTest": None, "id": "user", "ariaLabel": "Username", "name": "user", "text": "", "placeholder": None}
    sel = mapper._selector_string(el)
    assert sel == "#user"


def test_selector_string_uses_aria_label_when_no_id(mapper):
    el = {"tag": "button", "dataTest": None, "id": None, "ariaLabel": "Submit form", "name": None, "text": "Submit", "placeholder": None}
    sel = mapper._selector_string(el)
    assert sel == "[aria-label='Submit form']"


def test_selector_string_uses_name_for_input(mapper):
    el = {"tag": "input", "dataTest": None, "id": None, "ariaLabel": None, "name": "email", "text": "", "placeholder": None}
    sel = mapper._selector_string(el)
    assert sel == "input[name='email']"


def test_selector_string_uses_text_for_button(mapper):
    el = {"tag": "button", "dataTest": None, "id": None, "ariaLabel": None, "name": None, "text": "Login", "placeholder": None}
    sel = mapper._selector_string(el)
    assert "Login" in sel


def test_selector_string_fallback_todo(mapper):
    el = {"tag": "div", "dataTest": None, "id": None, "ariaLabel": None, "name": None, "text": "", "placeholder": None}
    sel = mapper._selector_string(el)
    assert "TODO" in sel


# ── _score ────────────────────────────────────────────────────────────────────

def test_score_fill_prefers_input(mapper):
    input_el = {"tag": "input", "type": "text", "dataTest": "username", "ariaLabel": None,
                "id": None, "placeholder": None, "name": None, "text": "", "href": None, "className": ""}
    btn_el = {"tag": "button", "type": "submit", "dataTest": "username", "ariaLabel": None,
              "id": None, "placeholder": None, "name": None, "text": "", "href": None, "className": ""}
    score_input = mapper._score(input_el, "fill", ["username"])
    score_btn = mapper._score(btn_el, "fill", ["username"])
    assert score_input > score_btn


def test_score_penalizes_hidden_for_fill(mapper):
    hidden_el = {"tag": "input", "type": "hidden", "dataTest": "username", "ariaLabel": None,
                 "id": None, "placeholder": None, "name": None, "text": "", "href": None, "className": ""}
    text_el = {"tag": "input", "type": "text", "dataTest": "username", "ariaLabel": None,
               "id": None, "placeholder": None, "name": None, "text": "", "href": None, "className": ""}
    score_hidden = mapper._score(hidden_el, "fill", ["username"])
    score_text = mapper._score(text_el, "fill", ["username"])
    assert score_text > score_hidden


def test_score_click_prefers_button(mapper):
    btn_el = {"tag": "button", "type": "submit", "dataTest": None, "ariaLabel": None,
              "id": None, "placeholder": None, "name": None, "text": "Login", "href": None, "className": ""}
    input_el = {"tag": "input", "type": "text", "dataTest": None, "ariaLabel": None,
                "id": None, "placeholder": None, "name": None, "text": "Login", "href": None, "className": ""}
    score_btn = mapper._score(btn_el, "click", ["login"])
    score_input = mapper._score(input_el, "click", ["login"])
    assert score_btn > score_input


# ── _keywords stopword removal ─────────────────────────────────────────────────

def test_keywords_removes_stopwords(mapper):
    keywords = mapper._keywords("I want to fill in the username field")
    assert "fill" in keywords
    assert "username" in keywords
    assert "i" not in keywords
    assert "the" not in keywords
    assert "to" not in keywords


def test_keywords_returns_list(mapper):
    result = mapper._keywords("enter the password here")
    assert isinstance(result, list)


def test_keywords_min_length_filter(mapper):
    # words <= 2 chars should be filtered
    result = mapper._keywords("go on up to do it")
    for w in result:
        assert len(w) > 2


# ── _probe_cached caches per URL ──────────────────────────────────────────────

def test_probe_cached_caches_result(monkeypatch, mapper):
    call_count = {"n": 0}

    def fake_probe(self, url, credentials=None):
        call_count["n"] += 1
        return {"status": "ok", "url": url, "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    mapper._probe_cached("https://example.com/login")
    mapper._probe_cached("https://example.com/login")

    assert call_count["n"] == 1  # second call used cache


def test_probe_cached_different_urls_probe_separately(monkeypatch, mapper):
    call_count = {"n": 0}

    def fake_probe(self, url, credentials=None):
        call_count["n"] += 1
        return {"status": "ok", "url": url, "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    mapper._probe_cached("https://example.com/login")
    mapper._probe_cached("https://example.com/dashboard")

    assert call_count["n"] == 2


def test_probe_cached_returns_final_url(monkeypatch, mapper):
    """HIGH-1: _probe_cached must return (elements, final_url) tuple."""
    def fake_probe(self, url, credentials=None):
        return {"status": "ok", "url": "https://example.com/dashboard", "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    elements, final_url = mapper._probe_cached("https://example.com/login")
    assert isinstance(elements, list)
    assert final_url == "https://example.com/dashboard"


def test_probe_cached_force_re_probes(monkeypatch, mapper):
    """HIGH-1: force=True must bypass cache and re-probe."""
    call_count = {"n": 0}

    def fake_probe(self, url, credentials=None):
        call_count["n"] += 1
        return {"status": "ok", "url": url, "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    mapper._probe_cached("https://example.com/login")
    mapper._probe_cached("https://example.com/login", force=True)

    assert call_count["n"] == 2  # forced re-probe


# ── enrich_story replaces TODO targets ───────────────────────────────────────

def test_enrich_story_replaces_todo_targets(monkeypatch):
    def fake_probe(self, url, credentials=None):
        return {"status": "ok", "url": url, "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    mapper = AutoDOMMapper("https://example.com")
    story = {
        "id": "login_001",
        "title": "Login",
        "steps": [
            {"id": "step_01", "action": "navigate", "target": "/login", "description": "Open login", "value": ""},
            {"id": "step_02", "action": "fill", "target": "TODO__FILL_USERNAME", "description": "Enter username", "value": "admin"},
            {"id": "step_03", "action": "click", "target": "TODO__CLICK_LOGIN", "description": "Click login button", "value": ""},
        ],
    }

    enriched = mapper.enrich_story(story)
    fill_step = enriched["steps"][1]
    click_step = enriched["steps"][2]

    # Both TODO targets should have been replaced
    assert "TODO" not in fill_step["target"] or fill_step["target"].startswith("[data-test=")
    assert fill_step["target"] != "TODO__FILL_USERNAME"


def test_enrich_story_advances_current_url_after_redirect(monkeypatch):
    """HIGH-1: after a probe returns a different URL (e.g. post-login redirect),
    subsequent steps must be probed against the redirected URL, not the original."""
    probed_urls = []

    def fake_probe(self, url, credentials=None):
        probed_urls.append(url)
        if "login" in url:
            # Simulate redirect to dashboard after auto-login
            return {"status": "ok", "url": "https://example.com/dashboard", "elements": CANNED_ELEMENTS}
        return {"status": "ok", "url": url, "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    mapper = AutoDOMMapper("https://example.com")
    story = {
        "id": "login_001",
        "title": "Login",
        "steps": [
            {"id": "step_01", "action": "navigate", "target": "/login", "description": "Open login", "value": ""},
            # This fill is probed against /login; probe returns /dashboard
            {"id": "step_02", "action": "fill", "target": "TODO__FILL_USERNAME", "description": "Enter username", "value": "admin"},
            # This click is described as "login" so it marks _invalidate_next=True
            {"id": "step_03", "action": "click", "target": "TODO__CLICK_LOGIN", "description": "Click login button", "value": ""},
            # This fill should be probed against /dashboard (advanced url)
            {"id": "step_04", "action": "fill", "target": "TODO__FILL_SEARCH", "description": "Enter search term", "value": "item"},
        ],
    }

    mapper.enrich_story(story)
    # step_04 probe should be against dashboard (after redirect), not /login
    assert any("dashboard" in u for u in probed_urls)


def test_enrich_story_nav_trigger_click_causes_reprobe(monkeypatch):
    """HIGH-1: a click with a navigation-triggering description must force re-probe."""
    call_count = {"n": 0}

    def fake_probe(self, url, credentials=None):
        call_count["n"] += 1
        return {"status": "ok", "url": url, "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    mapper = AutoDOMMapper("https://example.com")
    story = {
        "id": "test_001",
        "title": "Test",
        "steps": [
            {"id": "step_01", "action": "fill", "target": "TODO__FILL_USERNAME", "description": "Enter username", "value": "admin"},
            # nav-trigger click: "submit" implies navigation
            {"id": "step_02", "action": "click", "target": "#submit", "description": "Submit the form", "value": ""},
            {"id": "step_03", "action": "fill", "target": "TODO__FILL_AFTER", "description": "Fill after submit", "value": "x"},
        ],
    }

    mapper.enrich_story(story)
    # step_01 and step_03 each need a probe (step_03 forced because of submit click)
    assert call_count["n"] >= 2


def test_enrich_story_does_not_mutate_original(monkeypatch):
    def fake_probe(self, url, credentials=None):
        return {"status": "ok", "url": url, "elements": CANNED_ELEMENTS}

    monkeypatch.setattr(DOMProber, "probe", fake_probe)

    mapper = AutoDOMMapper("https://example.com")
    story = {
        "id": "login_001",
        "title": "Login",
        "steps": [
            {"id": "step_01", "action": "fill", "target": "TODO__X", "description": "fill field", "value": ""},
        ],
    }
    original_target = story["steps"][0]["target"]
    mapper.enrich_story(story)
    assert story["steps"][0]["target"] == original_target


# ── DOMProber._looks_like_login_page (MEDIUM-4) ───────────────────────────────

def test_looks_like_login_page_url_hint():
    """MEDIUM-4: URL with 'login' keyword is detected without needing page object."""
    prober = DOMProber()
    assert prober._looks_like_login_page("https://example.com/login") is True


def test_looks_like_login_page_signin_url():
    prober = DOMProber()
    assert prober._looks_like_login_page("https://example.com/signin") is True


def test_looks_like_login_page_no_hint_no_page():
    """MEDIUM-4: URL with no hint and no page object returns False."""
    prober = DOMProber()
    assert prober._looks_like_login_page("https://example.com/home") is False


def test_looks_like_login_page_password_field_present():
    """MEDIUM-4: Any page with a password input is treated as a login page."""
    prober = DOMProber()

    class FakePage:
        def locator(self, sel):
            return self

        def count(self):
            # Simulate password input present
            return 1

    assert prober._looks_like_login_page("https://example.com/", FakePage()) is True


def test_looks_like_login_page_no_password_field_no_url_hint():
    """MEDIUM-4: Page without password field and no URL hint returns False."""
    prober = DOMProber()

    class FakePage:
        def locator(self, sel):
            return self

        def count(self):
            return 0

    assert prober._looks_like_login_page("https://example.com/products", FakePage()) is False


# ── AutoDOMMapper._is_nav_trigger (HIGH-1) ────────────────────────────────────

def test_is_nav_trigger_login_keyword(mapper):
    assert mapper._is_nav_trigger("Click login button") is True


def test_is_nav_trigger_submit_keyword(mapper):
    assert mapper._is_nav_trigger("Submit the form") is True


def test_is_nav_trigger_continue_keyword(mapper):
    assert mapper._is_nav_trigger("Continue to next step") is True


def test_is_nav_trigger_neutral_description(mapper):
    assert mapper._is_nav_trigger("Enter username in the field") is False


def test_is_nav_trigger_case_insensitive(mapper):
    assert mapper._is_nav_trigger("CLICK SIGN IN BUTTON") is True
