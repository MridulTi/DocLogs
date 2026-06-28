import typer
from pathlib import Path
from typing import Optional

import yaml

from helper.paths import config_path, ensure_config


def load_config(path: Path | None = None) -> dict[str, object]:
    config_file = path or ensure_config()
    if not config_file.exists():
        raise typer.Exit(code=1, message=f"Config file not found: {config_file}")
    with config_file.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def register(app: typer.Typer):

    @app.command("config", help="Show the active DocLogs configuration.")
    def config(
        path: Optional[Path] = typer.Option(None, "-c", "--config", help="Path to the config file."),
    ) -> None:
        """Print the active DocLogs configuration."""
        active = path or ensure_config()
        settings = load_config(active)
        typer.echo(f"Active DocLogs configuration ({active}):")
        typer.echo(settings)
