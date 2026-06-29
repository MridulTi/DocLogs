from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from helper.llm.config import resolved_cli_model
from helper.llm.base import ProviderError


class CopilotCliProvider:
    name = "copilot"

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.command = settings.get("command", "copilot")
        self.model = resolved_cli_model(settings.get("model"))
        self.timeout_seconds = int(settings.get("timeout_seconds", 120))

    def is_available(self) -> bool:
        return bool(shutil.which(self.command))

    def availability_hint(self) -> str:
        if self.is_available():
            return f"Found `{self.command}`. Authenticate with GitHub if generation fails."
        return (
            "Install GitHub Copilot CLI: "
            "https://docs.github.com/en/copilot/how-tos/copilot-cli"
        )

    def generate(self, prompt: str) -> str:
        if not self.is_available():
            raise ProviderError(self.availability_hint())

        with tempfile.TemporaryDirectory() as tmpdir:
            share_path = Path(tmpdir) / "copilot-session.md"
            command = [
                self.command,
                "-p",
                prompt,
                "-s",
                "--no-ask-user",
                f"--share={share_path}",
            ]
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
                    f"Copilot CLI timed out after {self.timeout_seconds}s"
                ) from exc

            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "").strip()
                raise ProviderError(
                    f"Copilot CLI failed (exit {result.returncode}). "
                    f"{detail or self.availability_hint()}"
                )

            output = result.stdout.strip()
            if output:
                return output

            if share_path.exists():
                transcript = share_path.read_text(encoding="utf-8").strip()
                if transcript:
                    return transcript

        raise ProviderError("Copilot CLI returned empty output.")
