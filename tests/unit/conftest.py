"""
Unit test conftest — puts repo root on sys.path so framework modules import correctly.
Does NOT pull in the root tests/conftest.py fixtures (no page/browser fixtures here).
"""
from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
