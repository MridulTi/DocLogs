from __future__ import annotations

import re

DETAILS_LATER = "status: details_later"


def parse_task_blocks(notes: str | None) -> list[str]:
    """Split manual notes into task blocks (legacy block + ### Task N sections)."""
    if not notes or not notes.strip():
        return []
    blocks = re.split(r"(?=### Task \d+)", notes.strip())
    return [block.strip() for block in blocks if block.strip()]


def extract_worked_on(block: str) -> str | None:
    return _extract_worked_on(block)


def extract_topic(block: str) -> str | None:
    return _extract_field(
        block,
        "topic",
        stop_fields=("worked_on", "impact", "blockers", "remember", "status", "### Task"),
    )


def story_title(block: str) -> str | None:
    """Short label for weekly/generate; prefers topic over worked_on."""
    return extract_topic(block) or extract_worked_on(block)


def normalize_title(text: str) -> str:
    """Collapse whitespace and lowercase for fuzzy title matching."""
    return " ".join(text.strip().lower().split())


def list_incomplete_tasks(notes: str | None) -> list[tuple[int, str]]:
    if not notes:
        return []

    results: list[tuple[int, str]] = []

    for block in parse_task_blocks(notes):
        if DETAILS_LATER not in block:
            continue
        match = re.search(r"### Task (\d+)", block)
        task_num = int(match.group(1)) if match else 0
        summary = story_title(block) or (f"Task {task_num}" if task_num else "Incomplete entry")
        results.append((task_num, summary))

    return results


def _extract_worked_on(block: str) -> str | None:
    return _extract_field(
        block,
        "worked_on",
        stop_fields=("topic", "impact", "blockers", "remember", "status", "### Task"),
    )


def _extract_field(block: str, field: str, *, stop_fields: tuple[str, ...]) -> str | None:
    stops = "|".join(re.escape(name) for name in stop_fields)
    pattern = rf"{field}:\s*(.+?)(?=\n(?:{stops}|\Z))"
    match = re.search(pattern, block, re.DOTALL)
    if not match:
        return None
    return " ".join(match.group(1).split())


def complete_task(notes: str, task_num: int, followup: str) -> str:
    if task_num == 0:
        pattern = r"^.*?(status: details_later.*?)(?=\n### Task \d+|\Z)"
        worked_on = _extract_worked_on(notes) or ""
        new_block = f"worked_on: {worked_on}\n{followup}"
    else:
        pattern = rf"### Task {task_num}\n.*?(?=(?:\n### Task \d+|\Z))"
        match = re.search(pattern, notes, re.DOTALL)
        if not match:
            raise ValueError(f"Task {task_num} not found")
        worked_on = _extract_worked_on(match.group(0)) or ""
        topic = extract_topic(match.group(0))
        topic_line = f"topic: {topic}\n" if topic else ""
        new_block = f"### Task {task_num}\n{topic_line}worked_on: {worked_on}\n{followup}"

    match = re.search(pattern, notes, re.DOTALL)
    if not match:
        raise ValueError(f"Task {task_num} not found")

    return notes[: match.start()] + new_block + notes[match.end() :]