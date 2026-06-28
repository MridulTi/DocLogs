from __future__ import annotations

from helper.prompts import load_prompt
from helper.sanitize import sanitize_with_review


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