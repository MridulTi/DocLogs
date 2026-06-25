from __future__ import annotations

from helper.entry import (
    DailyEntry,
    entry_path_for,
    load_entry,
    new_empty_entry,
)
from helper.git_collector import enrich_entry_from_git


def build_capture_entry(notes: str | None = None) -> DailyEntry:
    path = entry_path_for()
    existing = load_entry(path)

    entry = new_empty_entry()
    entry = enrich_entry_from_git(entry)

    if existing:
        if notes:
            if existing.notes and notes not in existing.notes:
                entry.notes = f"{existing.notes}\n{notes}"
            else:
                entry.notes = notes or existing.notes
        else:
            entry.notes = existing.notes

        entry.pr_titles = existing.pr_titles
        entry.ticket_ids = existing.ticket_ids
    else:
        entry.notes = notes

    return entry