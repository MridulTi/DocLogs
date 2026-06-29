import typer
from pathlib import Path
from typing import Optional

import yaml

from helper.llm import PROVIDER_NAMES, get_provider
from helper.llm.config import (
    load_llm_config,
    load_raw_config,
    provider_name_from_config,
    set_llm_provider,
)
from helper.paths import ensure_config
from helper.syntax import maybe_show_syntax


def load_config(path: Path | None = None) -> dict[str, object]:
    config_file = path or ensure_config()
    if not config_file.exists():
        raise typer.Exit(code=1, message=f"Config file not found: {config_file}")
    with config_file.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def _show_config(path: Path | None = None) -> None:
    active = path or ensure_config()
    settings = load_config(active)
    provider_name = provider_name_from_config(settings)

    typer.echo(f"Active DocLogs configuration ({active}):")
    typer.echo(settings)
    typer.echo("")
    typer.echo(f"Active provider: {provider_name}")
    typer.echo(f"Cursor CLI: {_provider_status('cursor')}")
    typer.echo(f"Copilot CLI: {_provider_status('copilot')}")
    typer.echo("")
    typer.echo("Change provider: doclog config set provider cursor|copilot|prompt_only")


def _provider_status(name: str) -> str:
    provider = get_provider(name)
    if provider.is_available():
        return "available"
    return f"not available — {provider.availability_hint()}"


def register(app: typer.Typer):
    config_app = typer.Typer(help="Show or update DocLogs configuration.")

    @config_app.callback(invoke_without_command=True)
    def config_root(
        ctx: typer.Context,
        path: Optional[Path] = typer.Option(None, "-c", "--config", help="Path to the config file."),
        syntax: bool = typer.Option(False, "--syntax", help="Show command syntax, options, and examples."),
    ) -> None:
        if syntax and ctx.invoked_subcommand is None:
            maybe_show_syntax("config", True)
        if ctx.invoked_subcommand is not None:
            return
        _show_config(path)

    @config_app.command("set", help="Update a configuration value.")
    def config_set(
        key: str = typer.Argument(..., help="Setting name (currently: provider)."),
        value: str = typer.Argument(..., help="New value."),
        path: Optional[Path] = typer.Option(None, "-c", "--config", help="Path to the config file."),
        syntax: bool = typer.Option(False, "--syntax", help="Show command syntax, options, and examples."),
    ) -> None:
        maybe_show_syntax("config set", syntax)
        normalized_key = key.strip().lower().replace(".", "_")
        if normalized_key not in {"provider", "llm_provider"}:
            typer.echo(f"Unknown setting {key!r}. Supported: provider")
            raise typer.Exit(code=1)

        try:
            config_file = set_llm_provider(value, path)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=1) from exc

        typer.echo(f"Set llm.provider to {value.strip().lower()} in {config_file}")
        if value.strip().lower() != "prompt_only":
            selected = get_provider(value.strip().lower(), load_llm_config(config_file))
            if not selected.is_available():
                typer.echo(f"Warning: {selected.availability_hint()}")

    app.add_typer(config_app, name="config")
