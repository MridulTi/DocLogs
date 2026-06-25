import typer
from typing import *


def register(app: typer.Typer):

    @app.command("generate", help="run workflows")
    def generate(
    artifact_type: str = typer.Argument(
        ..., help="Artifact type to generate: blog, linkedin, resume, interview, changelog"
    ),
    title: Optional[str] = typer.Option(None, "-t", "--title", help="Optional title or story name."),
) -> None:
        """Generate a reusable artifact from a captured story."""
        typer.echo(f"✨ Generating {artifact_type} artifact")
        if title:
            typer.echo(f"Story title: {title}")
        typer.echo("This will use prompt templates and the configured model provider.")
