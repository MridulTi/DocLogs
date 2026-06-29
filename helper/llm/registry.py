from __future__ import annotations

from helper.llm.config import load_llm_config, provider_name_from_config, provider_settings
from helper.llm.copilot_cli import CopilotCliProvider
from helper.llm.cursor_cli import CursorCliProvider
from helper.llm.prompt_only import PromptOnlyProvider

PROVIDER_NAMES = ("prompt_only", "cursor", "copilot")


def resolve_provider_name(
    override: str | None = None,
    *,
    prompt_only: bool = False,
    config: dict[str, object] | None = None,
) -> str:
    if prompt_only:
        return "prompt_only"
    if override:
        return override.strip()
    return provider_name_from_config(config)


def get_provider(name: str, config: dict[str, object] | None = None) -> object:
    settings = config or load_llm_config()
    normalized = name.strip().lower()

    if normalized not in PROVIDER_NAMES:
        allowed = ", ".join(PROVIDER_NAMES)
        raise ValueError(f"Unknown provider {name!r}. Choose one of: {allowed}")

    if normalized == "prompt_only":
        return PromptOnlyProvider()
    if normalized == "cursor":
        return CursorCliProvider(provider_settings(settings, "cursor"))
    if normalized == "copilot":
        return CopilotCliProvider(provider_settings(settings, "copilot"))

    raise ValueError(f"Unknown provider {name!r}")
