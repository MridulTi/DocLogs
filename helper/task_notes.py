from __future__ import annotations

import re

DETAILS_LATER = "status: details_later"


def list_incomplete_tasks(notes: str | None) -> list[tuple[int, str]]:
    if not notes:
        return []

    results: list[tuple[int, str]] = []

    # Structured tasks: ### Task 2, ### Task 3, ...
    blocks = re.split(r"(?=### Task \d+)", notes)
    for block in blocks:
        if DETAILS_LATER not in block:
            continue
        match = re.search(r"### Task (\d+)", block)
        if not match:
            continue
        task_num = int(match.group(1))
        summary = _extract_worked_on(block) or f"Task {task_num}"
        results.append((task_num, summary))

    # Legacy / headerless stub (whole pre-task notes block)
    if DETAILS_LATER in notes and not results:
        summary = _extract_worked_on(notes) or "Incomplete entry"
        results.append((0, summary))  # 0 = no task number

    return results


def _extract_worked_on(block: str) -> str | None:
    match = re.search(
        r"worked_on:\s*(.+?)(?=\n(?:impact|blockers|remember|status:|### Task|\Z))",
        block,
        re.DOTALL,
    )
    if not match:
        return None
    return " ".join(match.group(1).split())  # flatten multiline YAML


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
        new_block = f"### Task {task_num}\nworked_on: {worked_on}\n{followup}"

    match = re.search(pattern, notes, re.DOTALL)
    if not match:
        raise ValueError(f"Task {task_num} not found")

    return notes[: match.start()] + new_block + notes[match.end() :]