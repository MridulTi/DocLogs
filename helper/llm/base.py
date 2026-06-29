from __future__ import annotations

from typing import Protocol


class ProviderError(RuntimeError):
    """Raised when a provider cannot run or returns an error."""


class Provider(Protocol):
    name: str

    def is_available(self) -> bool:
        """Return True when the provider can be invoked on this machine."""
        ...

    def availability_hint(self) -> str:
        """Human-readable install or auth guidance when unavailable."""
        ...

    def generate(self, prompt: str) -> str:
        """Send a prompt to the provider and return generated text."""
        ...
