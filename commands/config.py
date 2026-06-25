import typer
from typing import *
from pathlib import Path
import yaml

CONFIG_FILE = Path(__file__).resolve().parent.parent/("config.yaml")


def load_config(path: Path = CONFIG_FILE) -> dict[str, object]:
    if not path.exists():
        raise typer.Exit(code=1, message=f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def register(app: typer.Typer):

    @app.command("config", help="run workflows")
    def config(path: Optional[Path] = typer.Option(None, "-c", "--config", help="Path to the config file.")) -> None:
        """Print the active DocLogs configuration."""
        config_path = path or CONFIG_FILE
        config = load_config(config_path)
        typer.echo("Active DocLogs configuration:")
        typer.echo(config)