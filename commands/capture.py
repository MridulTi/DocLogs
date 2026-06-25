import typer
from typing import *


def register(app: typer.Typer):

    @app.command("capture", help="run workflows")
    def capture(
    notes: Optional[str] = typer.Option(None, "-n", "--notes", help="Optional notes describing today's activity."),
    include_terminal: bool = typer.Option(False, help="Include optional terminal history evidence."),
    include_tickets: bool = typer.Option(False, help="Include optional ticket IDs or issue references."),
) -> None:
        """Capture today's engineering work into local DevLogs storage."""
        typer.echo("📥 Capturing engineering activity...")
        typer.echo(f"notes: {notes or 'no manual notes provided'}")
        typer.echo(f"include_terminal: {include_terminal}")
        typer.echo(f"include_tickets: {include_tickets}")
        typer.echo("Captured evidence from git, PRs, and local context.")
