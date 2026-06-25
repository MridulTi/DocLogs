import typer
from typing import *

from helper.capture import build_capture_entry
from helper.entry import save_entry
from helper.git_collector import find_git_root




def register(app: typer.Typer):

    @app.command("capture", help="run workflows")
    def capture(
    notes: Optional[str] = typer.Option(None, "-n", "--notes", help="Optional notes describing today's activity."),
    include_terminal: bool = typer.Option(False, help="Include optional terminal history evidence."),
    include_tickets: bool = typer.Option(False, help="Include optional ticket IDs or issue references."),
) -> None:
        """Capture today's engineering work into local DocLogs storage."""
        if find_git_root() is None:
            typer.echo("⚠️  Not inside a git repo — git evidence will be empty.")
        entry = build_capture_entry(notes=notes)
        path = save_entry(entry)
        typer.echo(f"📥 Captured to {path}")
        typer.echo(f"   branch: {entry.branch or 'n/a'}")
        typer.echo(f"   commits today: {len(entry.commits)}")
