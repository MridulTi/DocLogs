from __future__ import annotations

import os
import shutil
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"


def doclog_home() -> Path:
    override = os.environ.get("DOCLOG_HOME")
    home = Path(override).expanduser() if override else Path.home() / ".doclog"
    home.mkdir(parents=True, exist_ok=True)
    return home


def entries_dir() -> Path:
    path = doclog_home() / "entries"
    path.mkdir(parents=True, exist_ok=True)
    return path


def posts_dir() -> Path:
    path = doclog_home() / "posts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = doclog_home() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def prompts_dir() -> Path:
    return TEMPLATES_DIR


def config_path() -> Path:
    return doclog_home() / "config.yaml"


def default_config_path() -> Path:
    return TEMPLATES_DIR / "config.yaml"


def ensure_config() -> Path:
    path = config_path()
    if path.exists():
        return path
    default = default_config_path()
    if default.exists():
        shutil.copy(default, path)
    else:
        path.write_text("llm:\n  provider: prompt_only\n", encoding="utf-8")
    return path
