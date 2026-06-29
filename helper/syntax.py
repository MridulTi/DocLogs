from __future__ import annotations

from dataclasses import dataclass

import typer


@dataclass(frozen=True)
class CommandSyntax:
    name: str
    summary: str
    usage: str
    options: tuple[str, ...]
    examples: tuple[str, ...]


SYNTAX: dict[str, CommandSyntax] = {
    "doclog": CommandSyntax(
        name="doclog",
        summary="Engineering career OS — capture work, review weekly, generate posts.",
        usage="doclog [COMMAND] [OPTIONS]",
        options=(
            "--help    Standard Typer/Click help for any command",
            "--syntax  Rich syntax, options, and examples for a command",
        ),
        examples=(
            "doclog --help",
            "doclog --syntax",
            "doclog capture --syntax",
            "doclog generate blog -t 1 --syntax",
            "doclog publish push --latest --syntax",
        ),
    ),
    "capture": CommandSyntax(
        name="capture",
        summary="Capture today's engineering work into ~/.doclog/entries/.",
        usage="doclog capture [OPTIONS]",
        options=(
            "-n, --notes TEXT       Notes text (skips interactive prompts)",
            "--no-interactive       Git-only capture; skip questions",
            "--include-terminal     Include terminal history (planned)",
            "--include-tickets      Include ticket IDs (planned)",
            "--syntax               Show this help with examples",
        ),
        examples=(
            "doclog capture",
            "doclog capture --no-interactive",
            'doclog capture -n "Fixed nginx TLS handshake with Akamai"',
            "doclog capture --syntax",
        ),
    ),
    "weekly": CommandSyntax(
        name="weekly",
        summary="Summarize recent captures and list story candidates.",
        usage="doclog weekly [OPTIONS]",
        options=(
            "--limit INT   Max stories to show (default: 5)",
            "--days INT    Days back to review (default: 7)",
            "--syntax      Show this help with examples",
        ),
        examples=(
            "doclog weekly",
            "doclog weekly --days 14 --limit 10",
            "doclog weekly --syntax",
        ),
    ),
    "generate": CommandSyntax(
        name="generate",
        summary="Build a post/artifact from a captured story.",
        usage="doclog generate ARTIFACT_TYPE [OPTIONS]",
        options=(
            "ARTIFACT_TYPE          blog | linkedin | resume | interview | changelog",
            "-t, --title TEXT       Story title, list number, or unique phrase",
            "--days INT             Days back to search (default: 7)",
            "--provider NAME        prompt_only | cursor | copilot",
            "--prompt-only          Write prompt file only",
            "--force                Send to provider even if sanitize flags exist",
            "--trust                Pass --trust to Cursor CLI",
            "--syntax               Show this help with examples",
        ),
        examples=(
            "doclog weekly",
            "doclog generate blog -t 1",
            'doclog generate blog -t "nginx akamai TLS"',
            "doclog config set provider cursor",
            "doclog generate blog -t 1 --trust",
            "doclog generate linkedin -t 2 --provider copilot",
            "doclog generate blog -t 1 --prompt-only",
            "doclog generate blog -t 1 --syntax",
        ),
    ),
    "sanitize": CommandSyntax(
        name="sanitize",
        summary="Redact sensitive content before sending text to an LLM.",
        usage="doclog sanitize [TEXT] [OPTIONS]",
        options=(
            "TEXT          Optional inline text to sanitize",
            "--syntax      Show this help with examples",
        ),
        examples=(
            "doclog sanitize",
            'doclog sanitize "internal URL https://corp.example.com failed"',
            "doclog sanitize --syntax",
        ),
    ),
    "config": CommandSyntax(
        name="config",
        summary="Show DocLogs configuration and provider availability.",
        usage="doclog config [OPTIONS]",
        options=(
            "-c, --config PATH   Custom config file path",
            "--syntax            Show this help with examples",
        ),
        examples=(
            "doclog config",
            "doclog config --syntax",
            "doclog config set provider cursor",
        ),
    ),
    "config set": CommandSyntax(
        name="config set",
        summary="Update a configuration value.",
        usage="doclog config set KEY VALUE [OPTIONS]",
        options=(
            "KEY           provider (sets llm.provider)",
            "VALUE         prompt_only | cursor | copilot",
            "-c, --config PATH   Custom config file path",
            "--syntax      Show this help with examples",
        ),
        examples=(
            "doclog config set provider cursor",
            "doclog config set provider copilot",
            "doclog config set provider prompt_only",
            "doclog config set provider cursor --syntax",
        ),
    ),
    "publish": CommandSyntax(
        name="publish",
        summary="Configure and push generated posts to a git repo.",
        usage="doclog publish [COMMAND] [OPTIONS]",
        options=(
            "--syntax   Show this help with examples",
        ),
        examples=(
            "doclog publish",
            "doclog publish set repo ~/projects/my-blog",
            "doclog publish push --latest",
            "doclog publish --syntax",
        ),
    ),
    "publish set": CommandSyntax(
        name="publish set",
        summary="Configure git publish settings in ~/.doclog/config.yaml.",
        usage="doclog publish set KEY VALUE",
        options=(
            "KEY     repo | branch | remote | subdir",
            "VALUE   Path or string value",
            "--syntax   Show this help with examples",
        ),
        examples=(
            "doclog publish set repo ~/projects/my-blog",
            "doclog publish set branch main",
            "doclog publish set remote origin",
            "doclog publish set subdir posts",
            "doclog publish set repo ~/projects/my-blog --syntax",
        ),
    ),
    "publish push": CommandSyntax(
        name="publish push",
        summary="Copy a post to the publish repo, commit, and push.",
        usage="doclog publish push [POST] [OPTIONS]",
        options=(
            "POST              Path to generated post (optional with --latest)",
            "-l, --latest      Push the newest generated post",
            "-m, --message TEXT   Custom git commit message",
            "--syntax          Show this help with examples",
        ),
        examples=(
            "doclog publish push --latest",
            "doclog publish push ~/.doclog/posts/nginx-fix-blog.md",
            'doclog publish push --latest -m "Add nginx TLS post"',
            "doclog publish push --latest --syntax",
        ),
    ),
}


def show_syntax(command_key: str) -> None:
    entry = SYNTAX.get(command_key)
    if entry is None:
        typer.echo(f"No syntax help for {command_key!r}.")
        typer.echo("Run doclog --syntax for an overview.")
        raise typer.Exit(code=1)

    typer.echo(f"{entry.name} — {entry.summary}\n")
    typer.echo(f"Usage:\n  {entry.usage}\n")
    if entry.options:
        typer.echo("Options:")
        for option in entry.options:
            typer.echo(f"  {option}")
        typer.echo("")
    if entry.examples:
        typer.echo("Examples:")
        for example in entry.examples:
            typer.echo(f"  {example}")
    if command_key == "doclog":
        typer.echo("\nCommands:")
        for key in (
            "capture",
            "weekly",
            "generate",
            "sanitize",
            "config",
            "config set",
            "publish",
            "publish set",
            "publish push",
        ):
            item = SYNTAX[key]
            typer.echo(f"  {item.name:<14} {item.summary}")
        typer.echo("\nTip: doclog <command> --syntax")
    raise typer.Exit()


def maybe_show_syntax(command_key: str, syntax: bool) -> None:
    if syntax:
        show_syntax(command_key)
