"""
MemoryEngine — thread-safe, process-safe persistent local JSON knowledge store.

Safety guarantees:
  - In-process: threading.RLock prevents concurrent mutation within one Python process.
  - Cross-process: filelock.FileLock prevents corruption under pytest-xdist or
    parallel framework run invocations.
  - Atomic writes: data is written to a temp file then os.replace()'d onto the DB
    path, so a crash mid-write never corrupts existing data.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

try:
    from filelock import FileLock, Timeout as FileLockTimeout
    _HAS_FILELOCK = True
except ImportError:  # pragma: no cover
    _HAS_FILELOCK = False

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


class MemoryEngine:
    CATEGORIES = ("selector", "quirk", "workflow", "failure", "general")

    def __init__(self, db_path: str = "memory/framework_memory.json") -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file = str(self.db_path.with_suffix(".lock"))
        self._rlock = threading.RLock()
        self._store: Dict[str, Dict[str, Any]] = {}
        self._load()

    # ── Lock helpers ──────────────────────────────────────────────────────────

    def _file_lock(self):
        if _HAS_FILELOCK:
            return FileLock(self._lock_file, timeout=10)
        return contextlib.nullcontext()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.db_path.exists():
            return
        try:
            with open(self.db_path, encoding="utf-8") as f:
                self._store = json.load(f)
            logger.info("Memory loaded: %d entries from %s", len(self._store), self.db_path)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Memory file unreadable, starting fresh: %s", exc)
            self._store = {}

    def _load_fresh(self) -> None:
        """Re-read from disk inside a lock to pick up concurrent changes."""
        if not self.db_path.exists():
            return
        try:
            with open(self.db_path, encoding="utf-8") as f:
                self._store = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass  # keep existing in-memory state

    def _save(self) -> None:
        """Atomic write: write to a sibling temp file, then os.replace onto db_path."""
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=self.db_path.parent,
            prefix=".memory_tmp_",
            suffix=".json",
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self._store, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.db_path)
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def _mutate(self, fn: Callable[[], _T]) -> _T:
        """Execute fn inside both in-process and cross-process locks with a fresh read."""
        with self._rlock:
            with self._file_lock():
                self._load_fresh()
                result = fn()
                self._save()
        return result

    # ── ID generation ─────────────────────────────────────────────────────────

    @staticmethod
    def _make_id(key: str, category: str) -> str:
        return hashlib.md5(f"{category}:{key}".encode()).hexdigest()[:12]

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    def remember(
        self,
        key: str,
        value: Any,
        category: str = "general",
        tags: Optional[List[str]] = None,
        confidence: float = 1.0,
    ) -> str:
        entry_id = self._make_id(key, category)
        now = time.time()

        def _do() -> str:
            if entry_id in self._store:
                entry = self._store[entry_id]
                entry["value"] = value
                entry["updated_at"] = now
                entry["confidence"] = confidence
                if tags:
                    entry["tags"] = sorted(set(entry.get("tags", []) + tags))
            else:
                self._store[entry_id] = {
                    "id": entry_id,
                    "key": key,
                    "value": value,
                    "category": category,
                    "tags": tags or [],
                    "confidence": confidence,
                    "created_at": now,
                    "updated_at": now,
                    "access_count": 0,
                }
            logger.debug("Memory stored: [%s] %s", category, key)
            return entry_id

        return self._mutate(_do)

    def recall(self, key: str, category: str = "general") -> Optional[Any]:
        """Read-only — does NOT write to disk to avoid unnecessary I/O."""
        with self._rlock:
            entry_id = self._make_id(key, category)
            entry = self._store.get(entry_id)
            return entry["value"] if entry else None

    def forget(self, key: str, category: str = "general") -> bool:
        entry_id = self._make_id(key, category)

        def _do() -> bool:
            if entry_id in self._store:
                del self._store[entry_id]
                return True
            return False

        return self._mutate(_do)

    # ── Retrieval helpers (read-only — no disk I/O) ───────────────────────────

    def recall_by_category(self, category: str) -> List[Dict[str, Any]]:
        with self._rlock:
            return [e for e in self._store.values() if e.get("category") == category]

    def recall_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        with self._rlock:
            return [e for e in self._store.values() if tag in e.get("tags", [])]

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        with self._rlock:
            return [
                e for e in self._store.values()
                if (
                    q in e.get("key", "").lower()
                    or q in str(e.get("value", "")).lower()
                    or any(q in t.lower() for t in e.get("tags", []))
                )
            ]

    # ── Domain-specific helpers ───────────────────────────────────────────────

    def record_failure(
        self,
        test_name: str,
        selector: str,
        error: str,
        fix: Optional[str] = None,
    ) -> str:
        return self.remember(
            key=f"failure:{test_name}",
            value={"selector": selector, "error": error, "fix": fix, "timestamp": time.time()},
            category="failure",
            tags=["failure", test_name],
        )

    def record_selector_fix(
        self,
        page_name: str,
        element_name: str,
        original: str,
        fixed: str,
        reason: str,
    ) -> str:
        return self.remember(
            key=f"{page_name}.{element_name}",
            value={"original_selector": original, "fixed_selector": fixed, "reason": reason},
            category="selector",
            tags=["selector_fix", page_name],
            confidence=0.9,
        )

    def add_quirk(self, page_name: str, description: str, tags: Optional[List[str]] = None) -> str:
        return self.remember(
            key=f"quirk:{page_name}:{int(time.time())}",
            value=description,
            category="quirk",
            tags=(tags or []) + [page_name],
        )

    # ── Reporting ─────────────────────────────────────────────────────────────

    def get_all_context(self) -> Dict[str, Any]:
        with self._rlock:
            by_category: Dict[str, int] = {cat: 0 for cat in self.CATEGORIES}
            for entry in self._store.values():
                cat = entry.get("category", "general")
                by_category[cat] = by_category.get(cat, 0) + 1
            return {
                "total_entries": len(self._store),
                "categories": by_category,
                "entries": list(self._store.values()),
            }

    def dump_summary(self) -> str:
        ctx = self.get_all_context()
        lines = [f"MemoryEngine — {ctx['total_entries']} entries ({self.db_path})"]
        for cat, count in ctx["categories"].items():
            if count:
                lines.append(f"  {cat:12s}: {count}")
        return "\n".join(lines)
