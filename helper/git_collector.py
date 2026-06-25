from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import date, timedelta
from helper.entry import DailyEntry, GitCommit

def _run_git(args: list[str],cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()

def find_git_root(start: Path | None = None) -> Path | None:
    start = start or Path.cwd()
    output = _run_git(["rev-parse","--show-toplevel"],start)
    return Path(output) if output else None

def get_current_branch(repo_root: Path) -> str | None:
    branch = _run_git(["rev-parse","--abbrev-ref","HEAD"],repo_root)
    return branch or None


def collect_commits_for_day(repo_root: Path, day: date | None=None) -> list[GitCommit]:
    day = day or date.today()
    since = f"{day.isoformat()} 00:00:00"
    until = f"{(day + timedelta(days=1)).isoformat()} 00:00:00"
    fmt = "%H|%s|%an|%aI"

    output = _run_git(
        [
            "log",
            f"--since={since}",
            f"--until={until}",
            f"--pretty=format:{fmt}",
        ],
        repo_root,
    )

    commits: list[GitCommit] =[]
    for line in output.splitlines():
        if not line:
            continue
        hash_,subject,author,commited_at = line.split("|",3)
        commits.append(
            GitCommit(
                hash=hash_,
                subject=subject,
                author=author,
                commited_at=commited_at
            )
        )
    return commits

def enrich_entry_from_git(entry: DailyEntry, repo_path: Path | None=None)-> DailyEntry:
    start = repo_path or Path.cwd()
    repo_root = find_git_root(start)
    if repo_root is None:
        return entry
    entry.repository_path = str(repo_root)
    entry.branch = get_current_branch(repo_root)
    entry.commits = collect_commits_for_day(
        repo_root,
        date.fromisoformat(entry.date),
    )
    return entry
