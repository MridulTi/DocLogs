from __future__ import annotations

import re

from helper.task_notes import extract_worked_on, normalize_title, parse_task_blocks
from helper.weekly import build_story_candidates, load_entries_for_days

_WEEKLY_DATE_SUFFIX = re.compile(r"\s+\(\d{4}-\d{2}-\d{2}\)\s*$")


def prepare_needle(title: str) -> str:
    needle = title.strip()
    needle = _WEEKLY_DATE_SUFFIX.sub("", needle)
    needle = needle.removesuffix(" [incomplete]").strip()
    return normalize_title(needle)


def find_story_text(title: str, days: int = 7) -> str | None:
    title_stripped = title.strip()
    if not title_stripped:
        return None

    if title_stripped.isdigit():
        candidates = build_story_candidates(load_entries_for_days(days), limit=100)
        index = int(title_stripped) - 1
        if 0 <= index < len(candidates):
            return find_story_text(candidates[index].title, days)
        return None

    needle = prepare_needle(title_stripped)
    if not needle:
        return None

    partial_matches: list[str] = []
    entries = load_entries_for_days(days)

    for entry in entries:
        for commit in entry.commits:
            candidate = normalize_title(commit.subject)
            if candidate == needle:
                return (
                    f"worked_on: {commit.subject}\n"
                    f"commit: {commit.hash}\n"
                    f"author: {commit.author}\n"
                    f"committed_at: {commit.commited_at}"
                )
            if _is_partial_match(needle, candidate):
                partial_matches.append(
                    f"worked_on: {commit.subject}\n"
                    f"commit: {commit.hash}\n"
                    f"author: {commit.author}\n"
                    f"committed_at: {commit.commited_at}"
                )

        for block in parse_task_blocks(entry.notes):
            task_title = extract_worked_on(block)
            if not task_title:
                continue
            candidate = normalize_title(task_title)
            if candidate == needle:
                return block
            if _is_partial_match(needle, candidate):
                partial_matches.append(block)

    if len(partial_matches) == 1:
        return partial_matches[0]
    return None


def _is_partial_match(needle: str, candidate: str) -> bool:
    if len(needle) < 8:
        return False
    return needle in candidate or candidate in needle
