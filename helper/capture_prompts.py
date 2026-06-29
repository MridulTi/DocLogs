from __future__ import annotations

import typer
import re

from helper.entry import entry_path_for, load_entry
from helper.task_notes import complete_task, list_incomplete_tasks

def maybe_complete_stub() -> str | None:
    entry = load_entry(entry_path_for())
    if not entry or not entry.notes:
        return None
    pending = list_incomplete_tasks(entry.notes)
    if not pending:
        return None
    typer.echo("\n📝 Incomplete tasks from today:\n")
    for num, summary in pending:
        typer.echo(f"  {num}. {summary[:70]}{'...' if len(summary) > 70 else ''}")
    if not typer.confirm("\nAdd details to one of these?", default=True):
        return None
    choice = typer.prompt("Task number", default=str(pending[0][0])).strip()
    task_num = int(choice)
    typer.echo("\n--- Completing task ---\n")
    followup = collect_followup_notes()
    if not followup:
        return None
    return complete_task(entry.notes, task_num, followup)



# (stored label, prompt shown to user, required)
CAPTURE_QUESTIONS: list[tuple[str, str, bool]] = [
    ("worked_on", "What did you work on today?", True),
    ("impact", "What was the impact or outcome?", False),
    ("blockers", "Any blockers, incidents, or debugging?", False),
    ("remember", "Anything worth remembering for later?", False),
]

FOLLOWUP_QUESTIONS: list[tuple[str, str]] = [
    ("impact", "What was the impact or outcome?"),
    ("blockers", "Any blockers, incidents, or debugging?"),
    ("remember", "Anything worth remembering for later?"),
]

def collect_followup_notes() -> str | None:
    lines: list[str] = []
    for key, prompt in FOLLOWUP_QUESTIONS:
        answer = typer.prompt(prompt, default="").strip()
        if answer:
            lines.append(f"{key}: {answer}")
    lines.append("status: complete")
    return "\n".join(lines) if lines else None

def _next_task_number() -> int:
    entry = load_entry(entry_path_for())
    if not entry or not entry.notes:
        return 1
    nums = [int(n) for n in re.findall(r"### Task (\d+)", entry.notes)]
    return max(nums, default=0) + 1


def iter_interactive_tasks(topic: str | None = None):
    updated = maybe_complete_stub()
    if updated:
        yield updated, True   # ← replace entire notes
    task_num = _next_task_number()
    first_task = True
    while True:
        typer.echo(f"\n--- Task {task_num} ---\n")
        default_topic = topic if first_task else None
        batch = collect_interactive_notes(default_topic=default_topic)
        first_task = False
        if batch:
            yield f"### Task {task_num}\n{batch}", False   # ← append new task
        if not typer.confirm("Add another task?", default=False):
            break
        task_num += 1

def collect_interactive_notes(default_topic: str | None = None) -> str | None:
    typer.echo("\n📋 Daily capture — answer briefly (Enter to skip optional questions)\n")

    topic_answer = typer.prompt(
        "Task topic (short name for weekly & generate)",
        default=default_topic or "",
    ).strip()
    worked_on = typer.prompt("What did you work on today?", default="").strip()
    if not worked_on:
        return None

    lines: list[str] = []
    if topic_answer:
        lines.append(f"topic: {topic_answer}")
    lines.append(f"worked_on: {worked_on}")

    if typer.confirm("Add more details later?", default=False):
        lines.append("status: details_later")
        return "\n".join(lines)

    for key, prompt, required in CAPTURE_QUESTIONS[1:]:  # skip worked_on, already asked
        answer = typer.prompt(prompt, default="").strip()
        if answer:
            lines.append(f"{key}: {answer}")

    lines.append("status: complete")
    return "\n".join(lines)