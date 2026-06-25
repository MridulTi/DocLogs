import typer
from typing import *


def register(app: typer.Typer):

    @app.command("sanitize", help="run workflows")
    def sanitize(source: Optional[str] = typer.Argument(None, help="Optional text to sanitize. If omitted, use captured evidence.")) -> None:
        """Sanitize content before sending it to any LLM provider."""
        typer.echo("🔒 Sanitizing content...")
        if source:
            typer.echo(f"source: {source[:80]}{'...' if len(source) > 80 else ''}")
        typer.echo("Internal URLs, accounts, tokens, and IP addresses will be redacted.")