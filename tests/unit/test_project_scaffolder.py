"""
Tests for ProjectScaffolder.
"""
from __future__ import annotations

import os

import pytest

from utils.helpers import ProjectScaffolder


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


# ── Web scaffolding ───────────────────────────────────────────────────────────

def test_scaffold_web_creates_expected_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "web")
    created = s.scaffold()
    assert len(created) >= 3  # locators, page, story, test
    paths = [os.path.basename(p) for p in created]
    # At least locator and page files
    assert any("locators" in p for p in created)
    assert any("_page" in p for p in created)


def test_scaffold_api_creates_expected_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "api")
    created = s.scaffold()
    assert len(created) >= 1
    assert any("api" in p for p in created)


def test_scaffold_both_creates_web_and_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "both")
    created = s.scaffold()
    has_web = any("_page" in p or "_locators" in p for p in created)
    has_api = any("api" in p for p in created)
    assert has_web
    assert has_api


def test_scaffold_idempotent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "both")
    first = s.scaffold()
    second = s.scaffold()
    assert second == []  # nothing new created on second call


def test_scaffold_name_normalization(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Spaces and hyphens should be normalized to underscores
    s = ProjectScaffolder("https://myapp.com", "My App", "web")
    assert s.name == "my_app"


def test_scaffold_name_with_hyphen(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "my-app", "web")
    assert s.name == "my_app"


def test_scaffold_generated_locators_compile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "web")
    s.scaffold()
    locator_file = tmp_path / "locators" / "myapp_locators.py"
    assert locator_file.exists()
    src = locator_file.read_text(encoding="utf-8")
    compile(src, "<test>", "exec")


def test_scaffold_generated_page_compiles(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "web")
    s.scaffold()
    page_file = tmp_path / "pages" / "myapp_page.py"
    assert page_file.exists()
    src = page_file.read_text(encoding="utf-8")
    compile(src, "<test>", "exec")


def test_scaffold_generated_test_compiles(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "web")
    s.scaffold()
    test_file = tmp_path / "tests" / "workflows" / "test_myapp.py"
    assert test_file.exists()
    src = test_file.read_text(encoding="utf-8")
    compile(src, "<test>", "exec")


def test_scaffold_url_stripped_of_trailing_slash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com/", "myapp", "web")
    assert not s.url.endswith("/")


def test_scaffold_class_name_capitalized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "myapp", "web")
    assert s.class_name == "Myapp"


def test_scaffold_multi_word_class_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = ProjectScaffolder("https://myapp.com", "my app", "web")
    # "My" + "App" -> "MyApp"
    assert s.class_name == "MyApp"
