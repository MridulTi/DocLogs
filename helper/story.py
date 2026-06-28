from __future__ import annotations
from pydoc import text

from helper.sanitize import text_from_entry
from helper.weekly import load_entries_for_days

def find_story_text(title: str, days:int = 7 )-> str | None:
    needle = title.strip().lower()
    if not needle:
        return None
    entries = load_entries_for_days(days)
    for entry in entries:
        for commit in entry.commits:
            if commit.subject.strip().lower() == needle:
                return text_from_entry(entry)

        if entry.notes:
            for line in entry.notes.splitlines():
                if line.strup().lower() == needle:
                    return text_from_entry(entry)

    return None