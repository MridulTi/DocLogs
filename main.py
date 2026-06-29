from __future__ import annotations

from pathlib import Path
import importlib
import typer

from helper.syntax import maybe_show_syntax


app = typer.Typer(
    help="DocLogs CLI: capture engineering activity, review weekly progress, and generate reusable career artifacts.",
)

COMMANDS_DIR = Path(__file__).resolve().parent / "commands"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    syntax: bool = typer.Option(
        False,
        "--syntax",
        help="Show command overview with syntax and examples.",
    ),
) -> None:
    if syntax and ctx.invoked_subcommand is None:
        maybe_show_syntax("doclog", True)


def discover_commands():
    for path in COMMANDS_DIR.iterdir():
        if path.is_file() and path.suffix == ".py" and path.name != "__init__.py":
            module = importlib.import_module(f"commands.{path.stem}")
            if hasattr(module, "register"):
                module.register(app)


discover_commands()

if __name__ == "__main__":
    app()
