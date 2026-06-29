from __future__ import annotations

from helper.llm.base import ProviderError


class PromptOnlyProvider:
    name = "prompt_only"

    def is_available(self) -> bool:
        return True

    def availability_hint(self) -> str:
        return "Writes a prompt file only; no external provider required."

    def generate(self, prompt: str) -> str:
        raise ProviderError("prompt_only does not call an external provider")
