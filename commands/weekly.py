from ast import Return
import typer
from typing import *
from helper.weekly import build_story_candidates, load_entries_for_days
from helper.syntax import maybe_show_syntax


def register(app: typer.Typer):

    @app.command("weekly", help="run workflows")
    def weekly(
        limit: int = typer.Option(5, help="Maximum number of story candidates to display."),
        days: int = typer.Option(7, help="How many days back to review."),
        syntax: bool = typer.Option(False, "--syntax", help="Show command syntax, options, and examples."),
        ) -> None:
        """Summarize the week and surface candidate stories for expansion."""
        maybe_show_syntax("weekly", syntax)
        entries = load_entries_for_days(days)
        if not entries:
            typer.echo(f"📅 No captures found in the last {days} days.")
            typer.echo('Run: doclog capture --notes "what you worked on today"')
            return
        typer.echo(f"📅 Weekly summary ({len(entries)} day(s) captured)")
        candidates = build_story_candidates(entries, limit=limit)

        if not candidates:
            typer.echo("No story candidates yet.")
            return
        for i, story in enumerate(candidates, start=1):
            typer.echo(f"{i}. [{story.source}] {story.title} ({story.date})")
        typer.echo("")
        typer.echo('Generate: doclog generate blog -t 1   (or a short unique phrase from the title)')
