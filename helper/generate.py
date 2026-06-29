from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from helper.llm.base import Provider
from helper.llm.prompt_only import PromptOnlyProvider
from helper.prompts import load_prompt
from helper.sanitize import sanitize_with_review


@dataclass
class GenerateResult:
    prompt: str
    findings: list
    flags: list
    provider_name: str
    prompt_path: Path
    artifact_path: Path | None = None
    artifact_text: str | None = None


def build_prompt(artifact_type: str, story_text: str) -> tuple[str, list, list]:
    template = load_prompt(artifact_type)
    sanitized, findings, flags = sanitize_with_review(story_text)

    final = (
        f"{template.strip()}\n\n"
        f"---\n\n"
        f"## Captured evidence (sanitized)\n\n"
        f"{sanitized.strip()}\n"
    )
    return final, findings, flags


def save_and_generate(
    prompt: str,
    findings: list,
    flags: list,
    provider: Provider,
    *,
    prompt_path: Path,
    artifact_path: Path | None = None,
) -> GenerateResult:
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")

    if isinstance(provider, PromptOnlyProvider) or artifact_path is None:
        return GenerateResult(
            prompt=prompt,
            findings=findings,
            flags=flags,
            provider_name=provider.name,
            prompt_path=prompt_path,
        )

    artifact_text = provider.generate(prompt)
    artifact_path.write_text(artifact_text, encoding="utf-8")
    return GenerateResult(
        prompt=prompt,
        findings=findings,
        flags=flags,
        provider_name=provider.name,
        prompt_path=prompt_path,
        artifact_path=artifact_path,
        artifact_text=artifact_text,
    )
