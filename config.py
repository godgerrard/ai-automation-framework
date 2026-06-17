"""
Central framework configuration.

Load order:
  1. Dataclass defaults
  2. config.json (if present)
  3. .env file via python-dotenv
  4. Environment variables (highest priority)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load .env early so os.getenv picks up its values below
load_dotenv()

# Resolve the repo root once so relative paths always anchor correctly
_REPO_ROOT = Path(__file__).parent.resolve()


@dataclass
class BrowserConfig:
    browser: str = "chromium"
    headless: bool = False
    slow_mo: int = 0
    timeout: int = 30_000
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})


@dataclass
class AppConfig:
    base_url: str = "http://localhost:3000"
    environment: str = "local"
    implicit_wait: int = 10
    explicit_wait: int = 30
    screenshot_on_failure: bool = True


@dataclass
class FrameworkConfig:
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    app: AppConfig = field(default_factory=AppConfig)
    # All paths are absolute (anchored to repo root)
    memory_db_path: str = str(_REPO_ROOT / "memory" / "framework_memory.json")
    reports_dir: str = str(_REPO_ROOT / "reports")
    stories_dir: str = str(_REPO_ROOT / "stories")
    pages_dir: str = str(_REPO_ROOT / "pages")
    tests_dir: str = str(_REPO_ROOT / "tests" / "workflows")
    locators_dir: str = str(_REPO_ROOT / "locators")


def load_config(config_path: Optional[str] = None) -> FrameworkConfig:
    config = FrameworkConfig()
    path = Path(config_path or (_REPO_ROOT / "config.json"))

    if path.exists():
        with open(path, encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)

        if "browser" in data:
            config.browser = BrowserConfig(**{
                k: v for k, v in data["browser"].items()
                if k in BrowserConfig.__dataclass_fields__
            })
        if "app" in data:
            config.app = AppConfig(**{
                k: v for k, v in data["app"].items()
                if k in AppConfig.__dataclass_fields__
            })
        for key in ("memory_db_path", "reports_dir", "stories_dir", "pages_dir", "tests_dir", "locators_dir"):
            if key in data:
                setattr(config, key, data[key])

    # Environment variable overrides (bidirectional)
    if url := os.getenv("BASE_URL"):
        config.app.base_url = url
    if browser := os.getenv("BROWSER"):
        config.browser.browser = browser
    headless_env = os.getenv("HEADLESS")
    if headless_env is not None:
        config.browser.headless = headless_env.strip().lower() in ("1", "true", "yes")

    return config


CONFIG = load_config()
