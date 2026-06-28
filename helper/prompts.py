from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

VALID_TYPES = {"blog", "linkedin", "resume", "interview", "changelog"}

def load_prompt(artifact_type: str) -> str:
    kind = artifact_type.strip().lower()
    if kind not in VALID_TYPES:
        raise ValueError(f"Unknown artifact type: {artifact_type}. Choose from: {', '.join(sorted(VALID_TYPES))}")
    path = PROMPTS_DIR / f"{kind}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")