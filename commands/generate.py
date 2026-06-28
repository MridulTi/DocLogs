import re

import typer
from typing import Optional

from helper.generate import build_prompt
from helper.paths import posts_dir
from helper.story import find_story_text


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
    ) -> None:
        if not title:
            typer.echo("Pass a story title: doclog generate blog -t \"Phase 0 completed\"")
            raise typer.Exit(code=1)

        story = find_story_text(title, days=days)
        if not story:
            typer.echo(f"Story not found: {title!r}")
            typer.echo("Run doclog weekly to see available titles.")
            raise typer.Exit(code=1)

        prompt, findings, flags = build_prompt(artifact_type, story)

        if flags:
            typer.echo("⚠️  Sensitive patterns flagged — review before sending to an LLM:")
            for flag in flags:
                typer.echo(f"  - [{flag.kind}] {flag.matched[:60]}")

        output_dir = posts_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / f"{slugify(title)}-{artifact_type}.md"
        out.write_text(prompt, encoding="utf-8")

        typer.echo(f"✨ Prompt saved to {out}")
        if findings:
            typer.echo(f"   ({len(findings)} item(s) redacted in evidence)")