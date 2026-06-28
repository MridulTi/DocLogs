from __future__ import annotations

from helper.entry import (
    entry_path_for,
    load_entry,
    new_empty_entry,
)
from helper.git_collector import enrich_entry_from_git


def merge_notes(*parts: str | None) -> str | None:
    chunks = [p.strip() for p in parts if p and p.strip()]
    if not chunks:
        return None
    return "\n\n".join(chunks)


def build_capture_entry(notes: str | None = None, *, replace_notes: bool = False):
    path = entry_path_for()
    existing = load_entry(path)

    entry = new_empty_entry()
    entry = enrich_entry_from_git(entry)

    if existing:
        entry.pr_titles = existing.pr_titles
        entry.ticket_ids = existing.ticket_ids

    if replace_notes:
        entry.notes = notes
        return entry

    if notes:
        if existing and existing.notes:
            if notes not in existing.notes:
                entry.notes = f"{existing.notes}\n\n{notes}"
            else:
                entry.notes = existing.notes
        else:
            entry.notes = notes
    elif existing:
        entry.notes = existing.notes

    return entry
