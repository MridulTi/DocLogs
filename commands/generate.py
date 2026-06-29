import re

import typer
from typing import Optional

from helper.generate import build_prompt, save_and_generate
from helper.llm import PROVIDER_NAMES, ProviderError, get_provider, resolve_provider_name
from helper.llm.config import load_llm_config, provider_settings
from helper.paths import posts_dir
from helper.story import find_story_text
from helper.syntax import maybe_show_syntax


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text).strip("-")


def register(app: typer.Typer):

    @app.command("generate", help="Generate a reusable artifact from a captured story.")
    def generate(
        artifact_type: str = typer.Argument(..., help="blog, linkedin, resume, interview, changelog"),
        title: Optional[str] = typer.Option(None, "-t", "--title", help="Story title from doclog weekly."),
        days: int = typer.Option(7, help="Days back to search for the story."),
        provider: Optional[str] = typer.Option(
            None,
            "--provider",
            help=f"Override LLM provider: {', '.join(PROVIDER_NAMES)}",
        ),
        prompt_only: bool = typer.Option(
            False,
            "--prompt-only",
            help="Write the sanitized prompt file only.",
        ),
        force: bool = typer.Option(
            False,
            "--force",
            help="Send to an external provider even when sanitize flags are present.",
        ),
        trust: bool = typer.Option(
            False,
            "--trust",
            help="Pass --trust to Cursor CLI (required for non-interactive agent runs).",
        ),
        syntax: bool = typer.Option(False, "--syntax", help="Show command syntax, options, and examples."),
    ) -> None:
        maybe_show_syntax("generate", syntax)
        if not title:
            typer.echo('Pass a story title: doclog generate blog -t "Phase 0 completed"')
            raise typer.Exit(code=1)

        story = find_story_text(title, days=days)
        if not story:
            typer.echo(f"Story not found: {title!r}")
            typer.echo("Run doclog weekly to see available titles.")
            typer.echo('Tip: use the list number, e.g. doclog generate blog -t 1')
            typer.echo('     or a short unique phrase (do not include the date in parentheses)')
            raise typer.Exit(code=1)

        config = load_llm_config()
        if trust:
            config = dict(config)
            cursor_cfg = dict(provider_settings(config, "cursor"))
            cursor_cfg["trust_workspace"] = True
            config["cursor"] = cursor_cfg
        try:
            provider_name = resolve_provider_name(
                provider,
                prompt_only=prompt_only,
                config=config,
            )
            selected_provider = get_provider(provider_name, config)
        except ValueError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=1) from exc

        if provider_name != "prompt_only" and not selected_provider.is_available():
            typer.echo(f"Provider {provider_name!r} is not available.")
            typer.echo(selected_provider.availability_hint())
            raise typer.Exit(code=1)

        prompt, findings, flags = build_prompt(artifact_type, story)

        if flags:
            typer.echo("Sensitive patterns flagged — review before sending to an external provider:")
            for flag in flags:
                typer.echo(f"  - [{flag.kind}] {flag.matched[:60]}")
            if provider_name != "prompt_only" and not force:
                slug = slugify(title)
                output_dir = posts_dir()
                output_dir.mkdir(parents=True, exist_ok=True)
                prompt_path = output_dir / f"{slug}-{artifact_type}-prompt.md"
                prompt_path.write_text(prompt, encoding="utf-8")
                typer.echo("Re-run with --force to send this prompt to the selected provider.")
                typer.echo(f"Prompt saved to {prompt_path}")
                raise typer.Exit(code=1)

        slug = slugify(title)
        output_dir = posts_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        if provider_name == "prompt_only":
            prompt_path = output_dir / f"{slug}-{artifact_type}.md"
            artifact_path = None
        else:
            prompt_path = output_dir / f"{slug}-{artifact_type}-prompt.md"
            artifact_path = output_dir / f"{slug}-{artifact_type}.md"

        try:
            result = save_and_generate(
                prompt,
                findings,
                flags,
                selected_provider,
                prompt_path=prompt_path,
                artifact_path=artifact_path,
            )
        except ProviderError as exc:
            prompt_path.write_text(prompt, encoding="utf-8")
            typer.echo(str(exc))
            typer.echo(f"Prompt saved to {prompt_path}")
            raise typer.Exit(code=1) from exc

        if provider_name == "prompt_only":
            typer.echo(f"Prompt saved to {result.prompt_path}")
        else:
            typer.echo(f"Prompt saved to {result.prompt_path}")
            typer.echo(f"Artifact saved to {result.artifact_path} (provider: {provider_name})")

        if findings:
            typer.echo(f"   ({len(findings)} item(s) redacted in evidence)")
