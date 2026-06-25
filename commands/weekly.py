import typer
from typing import *


def register(app: typer.Typer):

    @app.command("weekly", help="run workflows")
    def weekly(limit: int = typer.Option(5, help="Maximum number of story candidates to display.")) -> None:
        """Summarize the week and surface candidate stories for expansion."""
        typer.echo("📅 Weekly summary")
        typer.echo(f"Showing up to {limit} story candidates.")
        typer.echo("- Fixed EKS ingress issue")
        typer.echo("- Optimized Jenkins pipeline performance")
        typer.echo("- Automated IAM role provisioning")
