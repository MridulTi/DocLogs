from __future__ import annotations
from typing import *

from dataclasses import dataclass
from helper.entry import ENTRIES_DIR, DailyEntry, load_entry
from datetime import date, timedelta


@dataclass
class StoryCandidate:
    title: str
    source: str
    date: str

def load_entries_for_days(days: int = 7)-> list[DailyEntry]:
    entries: list[DailyEntry] = []
    today=date.today()
    for offset in range(days):
        day = today - timedelta(days=offset)
        path = ENTRIES_DIR / f"{day.isoformat()}.yaml"
        entry = load_entry(path)
        if entry:
            entries.append(entry)
    return entries


def build_story_candidates(entries: list[DailyEntry] | None = None,limit: int = 5)-> list[StoryCandidate]:
    candidates: list[StoryCandidate] =[]
    seen: set[str] = set()

    for entry in entries:
        for commit in entry.commits:
            title = commit.subject.strip()
            key = title.lower()

            if title and key not in seen:
                seen.add(key)
                candidates.append(StoryCandidate(
                    title,
                    source="commit",
                    date=entry.date
                ))
        if entry.notes:
            for line in entry.notes.splitlines():
                title = line.strip()
                key = title.lower()
                if title and key not in seen:
                    seen.add(key)
                    candidates.append(StoryCandidate(title,"notes",entry.date))

        if len(candidates) >= limit:
            break
    return candidates[:limit]