from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml


app = typer.Typer(help="DevLogs CLI: capture engineering activity, review weekly progress, and generate reusable career artifacts.")

COMMANDS_DIR = Path(__file__).parent.parent / "commands"


def discover_commands():
    commands = []
    for path in COMMANDS_DIR.iterdir():
        if path.is_file() and path.suffix == ".py" and path.name != "__init__.py":
            module=importlib.import_module(f"commands.{path.stem}")
            if hasattr(module,"register"):
                module.register(app)
discover_commands()

if __name__ == "__main__":
    app()
