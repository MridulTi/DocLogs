from __future__ import annotations
from dataclasses import dataclass
import datetime
from pathlib import Path
import yaml
from dataclasses import dataclass, field, asdict
from datetime import date, timezone, datetime, timedelta

from helper.paths import entries_dir


@dataclass
class GitCommit:
    hash: str
    subject: str
    author: str
    commited_at: str

@dataclass
class DailyEntry:
    date: str  # YYYY-MM-DD
    captured_at: str  # ISO 8601
    schema_version: int = SCHEMA_VERSION
    repository_path: str | None = None
    branch: str | None = None
    commits: list[GitCommit] = field(default_factory=list)
    notes: str | None = None
    pr_titles: list[str] = field(default_factory=list)
    ticket_ids: list[str] = field(default_factory=list)


def entry_path_for(day:date | None = None) -> Path:
    day = day or date.today()
    return entries_dir() / f"{day.isoformat()}.yaml"

def new_empty_entry(notes: str | None = None) -> DailyEntry:
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST).replace(microsecond=0)
    return DailyEntry(
        date = now.date().isoformat(),
        captured_at = now.isoformat(),
        notes = notes,
    )

def entry_to_dict(entry: DailyEntry) -> dict[str, Any]:
    data = asdict(entry)
    return {
        "schema_version": data["schema_version"],
        "date": data["date"],
        "captured_at": data["captured_at"],
        "repository": {
            "path": data["repository_path"],
            "branch": data["branch"],
        },
        "git": {
            "commits": data["commits"],
        },
        "manual": {
            "notes": data["notes"],
        },
        "evidence": {
            "pr_titles": data["pr_titles"],
            "ticket_ids": data["ticket_ids"],
        },
    }

def save_entry(entry: DailyEntry, path: Path | None = None) -> Path:
    target = path or entry_path_for()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            entry_to_dict(entry),
            stream,
            sort_keys=False,
            allow_unicode=True,
        )
    return target

def load_entry(path: Path | None=None)-> DailyEntry | None:
    target = path or entry_path_for()
    if not target.exists():
        return None

    with target.open('r',encoding='utf-8') as stream:
        data = yaml.safe_load(stream)
    if not data:
        return None

    commits =[
        GitCommit(**commit)
        for commit in data.get(f"git",{}).get("commits",[])
    ]

    return DailyEntry(
        date=data["date"],
        captured_at=data["captured_at"],
        schema_version=data.get("schema_version", SCHEMA_VERSION),
        repository_path=data.get("repository", {}).get("path"),
        branch=data.get("repository", {}).get("branch"),
        commits=commits,
        notes=data.get("manual", {}).get("notes"),
        pr_titles=data.get("evidence", {}).get("pr_titles", []),
        ticket_ids=data.get("evidence", {}).get("ticket_ids", []),
    )

