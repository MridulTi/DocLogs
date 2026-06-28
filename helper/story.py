from __future__ import annotations

from helper.task_notes import extract_worked_on, parse_task_blocks
from helper.weekly import load_entries_for_days


def find_story_text(title: str, days: int = 7) -> str | None:
    needle = title.strip().lower()
    if not needle:
        return None

    # Allow matching without [incomplete] suffix from weekly output
    needle = needle.removesuffix(" [incomplete]").strip()

    entries = load_entries_for_days(days)
    for entry in entries:
        for commit in entry.commits:
            if commit.subject.strip().lower() == needle:
                return (
                    f"worked_on: {commit.subject}\n"
                    f"commit: {commit.hash}\n"
                    f"author: {commit.author}\n"
                    f"committed_at: {commit.commited_at}"
                )

        for block in parse_task_blocks(entry.notes):
            task_title = extract_worked_on(block)
            if task_title and task_title.lower() == needle:
                return block

    return None
