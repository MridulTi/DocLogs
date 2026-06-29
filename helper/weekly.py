from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from helper.entry import DailyEntry, load_entry
from helper.paths import entries_dir
from helper.task_notes import DETAILS_LATER, parse_task_blocks, story_title


@dataclass
class StoryCandidate:
    title: str
    source: str
    date: str


def load_entries_for_days(days: int = 7) -> list[DailyEntry]:
    entries: list[DailyEntry] = []
    today = date.today()
    for offset in range(days):
        day = today - timedelta(days=offset)
        path = entries_dir() / f"{day.isoformat()}.yaml"
        entry = load_entry(path)
        if entry:
            entries.append(entry)
    return entries


def build_story_candidates(
    entries: list[DailyEntry] | None = None,
    limit: int = 5,
) -> list[StoryCandidate]:
    candidates: list[StoryCandidate] = []
    seen: set[str] = set()

    for entry in entries or []:
        for commit in entry.commits:
            title = commit.subject.strip()
            key = title.lower()
            if title and key not in seen:
                seen.add(key)
                candidates.append(
                    StoryCandidate(title=title, source="commit", date=entry.date)
                )

        for block in parse_task_blocks(entry.notes):
            title = story_title(block)
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            if DETAILS_LATER in block:
                title = f"{title} [incomplete]"
            candidates.append(
                StoryCandidate(title=title, source="task", date=entry.date)
            )

        if len(candidates) >= limit:
            break

    return candidates[:limit]
