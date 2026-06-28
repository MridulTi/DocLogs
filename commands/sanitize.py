import typer
from typing import *

from helper.entry import entry_path_for, load_entry
from helper.sanitize import redact, sanitize_with_review, text_from_entry


def register(app: typer.Typer):

    @app.command("sanitize",  help="Sanitize content before sending to an LLM.")
    def sanitize(
        source: Optional[str] = typer.Argument(None, help="Text to sanitize. If omitted, uses today's capture."),
    ) -> None:
        if source:
            text = source
        else:
            entry = load_entry(entry_path_for())
            if not entry:
                typer.echo("No capture for today. Run: doclog capture")
                raise typer.Exit(code=1)
            text = text_from_entry(entry)
        sanitized, findings, flags = sanitize_with_review(text)
        typer.echo("🔒 Sanitized output:\n")
        typer.echo(sanitized)
        if findings:
            typer.echo(f"\n({len(findings)} item(s) redacted)")
        else:
            typer.echo("\n(no sensitive patterns detected)")
        if flags:
            typer.echo("\n⚠️  Review before sending to LLM:")
            for flag in flags:
                snippet = flag.matched[:60] + ("..." if len(flag.matched) > 60 else "")
                typer.echo(f"  - [{flag.kind}] {snippet}")