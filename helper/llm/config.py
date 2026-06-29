from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from helper.paths import ensure_config

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def expand_env(value: object) -> object:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), match.group(0))

        return _ENV_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand_env(item) for item in value]
    return value


def load_llm_config(path: Path | None = None) -> dict[str, object]:
    config_file = path or ensure_config()
    with config_file.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    return expand_env(data)


def provider_name_from_config(config: dict[str, object] | None = None) -> str:
    settings = config or load_llm_config()
    llm = settings.get("llm", {})
    if isinstance(llm, dict):
        provider = llm.get("provider", "prompt_only")
        if isinstance(provider, str) and provider.strip():
            return provider.strip()
    return "prompt_only"


def provider_settings(config: dict[str, object], provider_name: str) -> dict[str, object]:
    section = config.get(provider_name, {})
    if isinstance(section, dict):
        return section
    return {}


def resolved_cli_model(model: object) -> str | None:
    """Return a CLI model name, or None to let the CLI pick its default (auto)."""
    if model is None:
        return None
    if not isinstance(model, str):
        return str(model)
    normalized = model.strip().lower()
    if not normalized or normalized == "auto":
        return None
    return model.strip()


def load_raw_config(path: Path | None = None) -> tuple[Path, dict[str, object]]:
    config_file = path or ensure_config()
    with config_file.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        data = {}
    return config_file, data


def save_config(settings: dict[str, object], path: Path | None = None) -> Path:
    config_file = path or ensure_config()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with config_file.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            settings,
            stream,
            sort_keys=False,
            allow_unicode=True,
        )
    return config_file


def set_llm_provider(provider: str, path: Path | None = None) -> Path:
    from helper.llm.registry import PROVIDER_NAMES

    normalized = provider.strip().lower()
    if normalized not in PROVIDER_NAMES:
        allowed = ", ".join(PROVIDER_NAMES)
        raise ValueError(f"Unknown provider {provider!r}. Choose one of: {allowed}")

    config_file, settings = load_raw_config(path)
    llm = settings.get("llm")
    if not isinstance(llm, dict):
        llm = {}
        settings["llm"] = llm
    llm["provider"] = normalized
    return save_config(settings, config_file)
