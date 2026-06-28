import typer
from typing import Optional

from helper.capture import build_capture_entry, merge_notes
from helper.capture_prompts import iter_interactive_tasks
from helper.entry import save_entry
from helper.git_collector import find_git_root


def _print_summary(entry, path) -> None:
    typer.echo(f"\n📥 Captured to {path}")
    typer.echo(f"   branch: {entry.branch or 'n/a'}")
    typer.echo(f"   commits today: {len(entry.commits)}")


def register(app: typer.Typer):

    @app.command("capture", help="Capture today's engineering work into local storage.")
    def capture(
        notes: Optional[str] = typer.Option(None, "-n", "--notes", help="Optional notes (skips interactive prompts)."),
        no_interactive: bool = typer.Option(False, "--no-interactive", help="Skip questions; git-only capture."),
        include_terminal: bool = typer.Option(False, help="Include optional terminal history evidence."),
        include_tickets: bool = typer.Option(False, help="Include optional ticket IDs or issue references."),
    ) -> None:
        if find_git_root() is None:
            typer.echo("⚠️  Not inside a git repo — git evidence will be empty.")

        # Interactive: multiple tasks in one session
        if not no_interactive and notes is None:
            path = None
            entry = None
            saved_any = False

            for batch, replace in iter_interactive_tasks():
                entry = build_capture_entry(notes=batch, replace_notes=replace)
                path = save_entry(entry)
                saved_any = True
                typer.echo("   ✓ Task saved" if not replace else "   ✓ Task updated")

            if not saved_any:
                entry = build_capture_entry(notes=None)
                path = save_entry(entry)

            _print_summary(entry, path)
            return

        # Non-interactive: git only or single --notes
        final_notes = merge_notes(notes)
        entry = build_capture_entry(notes=final_notes)
        path = save_entry(entry)
        _print_summary(entry, path)