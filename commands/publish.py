import typer
from pathlib import Path
from typing import Optional

from helper.publish_git import (
    PUBLISH_KEYS,
    PublishError,
    load_publish_config,
    push_post,
    resolve_post_file,
    set_publish_value,
)
from helper.syntax import maybe_show_syntax


def _show_publish_config() -> None:
    config = load_publish_config()
    typer.echo("Publish configuration:")
    typer.echo(f"  repo:   {config.repo_path or '(not set)'}")
    typer.echo(f"  branch: {config.branch}")
    typer.echo(f"  remote: {config.remote}")
    typer.echo(f"  subdir: {config.subdir}")
    typer.echo("")
    typer.echo("Configure: doclog publish set repo /path/to/clone")
    typer.echo("Push post: doclog publish push --latest")


def register(app: typer.Typer):
    publish_app = typer.Typer(help="Configure and push generated posts to a git repo.")

    @publish_app.callback(invoke_without_command=True)
    def publish_root(
        ctx: typer.Context,
        syntax: bool = typer.Option(False, "--syntax", help="Show command syntax, options, and examples."),
    ) -> None:
        if syntax and ctx.invoked_subcommand is None:
            maybe_show_syntax("publish", True)
        if ctx.invoked_subcommand is not None:
            return
        _show_publish_config()

    @publish_app.command("set", help="Configure the git repo used to publish posts.")
    def publish_set(
        key: str = typer.Argument(..., help=f"One of: {', '.join(sorted(PUBLISH_KEYS))}"),
        value: str = typer.Argument(..., help="Setting value."),
        syntax: bool = typer.Option(False, "--syntax", help="Show command syntax, options, and examples."),
    ) -> None:
        maybe_show_syntax("publish set", syntax)
        try:
            config_file = set_publish_value(key, value)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=1) from exc

        typer.echo(f"Set publish.{key.strip().lower()} in {config_file}")

    @publish_app.command("push", help="Copy a post into the publish repo, commit, and push.")
    def publish_push(
        post: Optional[Path] = typer.Argument(
            None,
            help="Path to a generated post under ~/.doclog/posts/",
        ),
        latest: bool = typer.Option(
            False,
            "--latest",
            "-l",
            help="Publish the most recently generated post.",
        ),
        message: Optional[str] = typer.Option(
            None,
            "-m",
            "--message",
            help="Custom git commit message.",
        ),
        syntax: bool = typer.Option(False, "--syntax", help="Show command syntax, options, and examples."),
    ) -> None:
        maybe_show_syntax("publish push", syntax)
        try:
            post_file = resolve_post_file(post, latest=latest)
            dest = push_post(post_file, load_publish_config(), message=message)
        except PublishError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=1) from exc

        typer.echo(f"Published {post_file.name}")
        typer.echo(f"  copied to {dest}")
        typer.echo(f"  pushed to remote")

    app.add_typer(publish_app, name="publish")
