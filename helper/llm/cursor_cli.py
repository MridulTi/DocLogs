from __future__ import annotations

import shutil
import subprocess
from typing import Any

from helper.llm.config import resolved_cli_model
from helper.llm.base import ProviderError


class CursorCliProvider:
    name = "cursor"

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.command = settings.get("command") or self._detect_command()
        self.model = resolved_cli_model(settings.get("model"))
        self.mode = settings.get("mode", "ask")
        self.timeout_seconds = int(settings.get("timeout_seconds", 120))
        self.trust_workspace = settings.get("trust_workspace", True)

    def _detect_command(self) -> str | None:
        for candidate in ("agent", "cursor-agent"):
            if shutil.which(candidate):
                return candidate
        return None

    def is_available(self) -> bool:
        return bool(self.command and shutil.which(self.command))

    def availability_hint(self) -> str:
        if self.is_available():
            return f"Found `{self.command}`. Run `{self.command} login` if generation fails."
        return "Install Cursor CLI: https://cursor.com/docs/cli — then run `agent login`."

    def generate(self, prompt: str) -> str:
        if not self.is_available():
            raise ProviderError(self.availability_hint())

        command = [self.command, "-p", prompt, f"--mode={self.mode}", "--output-format", "text"]
        if self.trust_workspace:
            command.append("--trust")
        if self.model:
            command.extend(["--model", str(self.model)])

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                f"Cursor CLI timed out after {self.timeout_seconds}s"
            ) from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise ProviderError(
                f"Cursor CLI failed (exit {result.returncode}). {detail or self.availability_hint()}"
            )

        output = result.stdout.strip()
        if not output:
            raise ProviderError("Cursor CLI returned empty output.")
        return output
