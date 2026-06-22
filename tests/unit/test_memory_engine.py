"""
Tests for MemoryEngine.
"""
from __future__ import annotations

import json
import threading
import time

import pytest

from core.memory_engine import MemoryEngine


@pytest.fixture
def mem(tmp_path):
    db = tmp_path / "memory" / "test_memory.json"
    return MemoryEngine(str(db))


# ── remember / recall ─────────────────────────────────────────────────────────

def test_remember_returns_id(mem):
    eid = mem.remember("key1", "value1")
    assert isinstance(eid, str)
    assert len(eid) == 12  # MD5 truncated to 12 chars


def test_recall_returns_stored_value(mem):
    mem.remember("mykey", "myvalue", category="general")
    result = mem.recall("mykey", category="general")
    assert result == "myvalue"


def test_recall_missing_key_returns_none(mem):
    assert mem.recall("nonexistent", category="general") is None


def test_remember_overwrites_value(mem):
    mem.remember("key1", "old", category="general")
    mem.remember("key1", "new", category="general")
    assert mem.recall("key1", category="general") == "new"


def test_update_preserves_created_at(mem):
    mem.remember("key1", "v1", category="general")
    # Read created_at from store
    eid = mem._make_id("key1", "general")
    created_at_before = mem._store[eid]["created_at"]

    time.sleep(0.01)
    mem.remember("key1", "v2", category="general")
    created_at_after = mem._store[eid]["created_at"]

    assert created_at_before == created_at_after


# ── forget ────────────────────────────────────────────────────────────────────

def test_forget_removes_entry(mem):
    mem.remember("del_key", "to_delete")
    result = mem.forget("del_key")
    assert result is True
    assert mem.recall("del_key") is None


def test_forget_missing_key_returns_false(mem):
    result = mem.forget("does_not_exist")
    assert result is False


# ── tag merge ─────────────────────────────────────────────────────────────────

def test_tag_merge_on_update(mem):
    mem.remember("tagged_key", "v1", tags=["a", "b"])
    mem.remember("tagged_key", "v2", tags=["c"])
    eid = mem._make_id("tagged_key", "general")
    tags = mem._store[eid]["tags"]
    assert "a" in tags
    assert "b" in tags
    assert "c" in tags


# ── search ────────────────────────────────────────────────────────────────────

def test_search_by_key(mem):
    mem.remember("login_selector", "#login-btn", category="selector")
    results = mem.search("login_selector")
    assert len(results) >= 1
    assert any(r["key"] == "login_selector" for r in results)


def test_search_by_value(mem):
    mem.remember("some_key", "unique_value_xyz", category="general")
    results = mem.search("unique_value_xyz")
    assert len(results) >= 1


def test_search_by_tag(mem):
    mem.remember("key_tagged", "val", tags=["mysearchtag"])
    results = mem.search("mysearchtag")
    assert len(results) >= 1


def test_search_no_results(mem):
    results = mem.search("completely_nonexistent_query_abc123")
    assert results == []


# ── recall_by_category ────────────────────────────────────────────────────────

def test_recall_by_category(mem):
    mem.remember("sel1", "val1", category="selector")
    mem.remember("wf1", "val2", category="workflow")
    sels = mem.recall_by_category("selector")
    assert all(e["category"] == "selector" for e in sels)
    assert len(sels) >= 1


def test_recall_by_category_empty(mem):
    result = mem.recall_by_category("failure")
    assert result == []


# ── recall_by_tag ─────────────────────────────────────────────────────────────

def test_recall_by_tag(mem):
    mem.remember("k1", "v1", tags=["special_tag"])
    mem.remember("k2", "v2", tags=["other_tag"])
    results = mem.recall_by_tag("special_tag")
    assert len(results) == 1
    assert results[0]["key"] == "k1"


# ── domain helpers ────────────────────────────────────────────────────────────

def test_record_selector_fix_category(mem):
    mem.record_selector_fix("login_page", "LOGIN_BTN", "#old", "#new", "corrector loop")
    results = mem.recall_by_category("selector")
    assert len(results) >= 1
    entry = results[0]
    assert entry["value"]["original_selector"] == "#old"
    assert entry["value"]["fixed_selector"] == "#new"


def test_record_failure_category(mem):
    mem.record_failure("test_login", "#login-btn", "Element not found")
    results = mem.recall_by_category("failure")
    assert len(results) >= 1


def test_add_quirk_category(mem):
    mem.add_quirk("checkout_page", "Sometimes shows a cookie popup")
    results = mem.recall_by_category("quirk")
    assert len(results) >= 1


# ── atomic write produces valid JSON ─────────────────────────────────────────

def test_atomic_write_produces_valid_json(mem, tmp_path):
    mem.remember("json_key", "json_value")
    content = mem.db_path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert isinstance(parsed, dict)


# ── dump_summary ──────────────────────────────────────────────────────────────

def test_dump_summary_nonempty(mem):
    mem.remember("k", "v")
    summary = mem.dump_summary()
    assert len(summary) > 0
    assert "MemoryEngine" in summary


def test_dump_summary_shows_entry_count(mem):
    mem.remember("a", "1")
    mem.remember("b", "2")
    summary = mem.dump_summary()
    assert "2" in summary


# ── get_all_context ───────────────────────────────────────────────────────────

def test_get_all_context_structure(mem):
    mem.remember("ctx_key", "ctx_val")
    ctx = mem.get_all_context()
    assert "total_entries" in ctx
    assert "categories" in ctx
    assert "entries" in ctx
    assert ctx["total_entries"] >= 1


# ── thread safety ─────────────────────────────────────────────────────────────

def test_thread_safety_10_threads(tmp_path):
    db = tmp_path / "memory" / "threaded_memory.json"
    mem = MemoryEngine(str(db))
    errors = []

    def worker(i):
        try:
            mem.remember(f"thread_key_{i}", f"value_{i}", category="general")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Thread errors: {errors}"
    ctx = mem.get_all_context()
    assert ctx["total_entries"] == 10
