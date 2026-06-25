from __future__ import annotations

from pathlib import Path
import importlib
import typer


app = typer.Typer(help="DocLogs CLI: capture engineering activity, review weekly progress, and generate reusable career artifacts.")

COMMANDS_DIR = Path(__file__).resolve().parent / "commands"

def discover_commands():
    for path in COMMANDS_DIR.iterdir():
        if path.is_file() and path.suffix == ".py" and path.name != "__init__.py":
            module=importlib.import_module(f"commands.{path.stem}")
            if hasattr(module,"register"):
                module.register(app)

discover_commands()

if __name__ == "__main__":
    app()
