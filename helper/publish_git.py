from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from helper.git_collector import find_git_root
from helper.llm.config import load_raw_config, save_config
from helper.paths import posts_dir

PUBLISH_KEYS = frozenset({"repo", "branch", "remote", "subdir"})


@dataclass
class PublishConfig:
    repo_path: Path | None
    branch: str = "main"
    remote: str = "origin"
    subdir: str = "posts"


class PublishError(RuntimeError):
    pass


def publish_config_from_settings(settings: dict[str, object]) -> PublishConfig:
    section = settings.get("publish", {})
    if not isinstance(section, dict):
        section = {}

    repo_raw = section.get("repo")
    repo_path = None
    if isinstance(repo_raw, str) and repo_raw.strip():
        repo_path = Path(repo_raw).expanduser().resolve()

    branch = section.get("branch", "main")
    remote = section.get("remote", "origin")
    subdir = section.get("subdir", "posts")

    return PublishConfig(
        repo_path=repo_path,
        branch=str(branch) if branch else "main",
        remote=str(remote) if remote else "origin",
        subdir=str(subdir) if subdir else "posts",
    )


def load_publish_config(path: Path | None = None) -> PublishConfig:
    _, settings = load_raw_config(path)
    return publish_config_from_settings(settings)


def set_publish_value(key: str, value: str, path: Path | None = None) -> Path:
    normalized = key.strip().lower()
    if normalized not in PUBLISH_KEYS:
        allowed = ", ".join(sorted(PUBLISH_KEYS))
        raise ValueError(f"Unknown publish setting {key!r}. Choose one of: {allowed}")

    config_file, settings = load_raw_config(path)
    publish = settings.get("publish")
    if not isinstance(publish, dict):
        publish = {}
        settings["publish"] = publish

    if normalized == "repo":
        repo_path = Path(value).expanduser().resolve()
        if not repo_path.exists():
            raise ValueError(f"Repo path does not exist: {repo_path}")
        if find_git_root(repo_path) is None:
            raise ValueError(f"Not a git repository: {repo_path}")
        publish["repo"] = str(repo_path)
    else:
        publish[normalized] = value.strip()

    return save_config(settings, config_file)


def latest_post_file() -> Path | None:
    candidates = [
        path
        for path in posts_dir().glob("*.md")
        if not path.name.endswith("-prompt.md")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def resolve_post_file(post: Path | None, *, latest: bool) -> Path:
    if post and latest:
        raise PublishError("Pass a post file or --latest, not both.")
    if latest:
        resolved = latest_post_file()
        if resolved is None:
            raise PublishError("No generated posts found in posts directory.")
        return resolved
    if post is None:
        raise PublishError("Pass a post file path or use --latest.")
    resolved = post.expanduser().resolve()
    if not resolved.exists():
        raise PublishError(f"Post file not found: {resolved}")
    if resolved.name.endswith("-prompt.md"):
        raise PublishError("Pass the generated artifact, not the prompt file.")
    return resolved


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def push_post(
    post_file: Path,
    config: PublishConfig,
    *,
    message: str | None = None,
) -> Path:
    if config.repo_path is None:
        raise PublishError(
            "Publish repo is not configured. Run: doclog publish set repo /path/to/clone"
        )

    repo_root = find_git_root(config.repo_path)
    if repo_root is None:
        raise PublishError(f"Not a git repository: {config.repo_path}")

    dest_dir = repo_root / config.subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / post_file.name
    shutil.copy2(post_file, dest_file)

    rel_path = dest_file.relative_to(repo_root).as_posix()
    status = _run_git(["status", "--porcelain", "--", rel_path], repo_root)
    if status.returncode != 0:
        raise PublishError(status.stderr.strip() or "git status failed")

    if not status.stdout.strip():
        raise PublishError(f"No changes to publish for {dest_file.name} (already up to date).")

    add = _run_git(["add", "--", rel_path], repo_root)
    if add.returncode != 0:
        raise PublishError(add.stderr.strip() or "git add failed")

    commit_message = message or f"doclog: add post {post_file.stem}"
    commit = _run_git(["commit", "-m", commit_message], repo_root)
    if commit.returncode != 0:
        raise PublishError(commit.stderr.strip() or commit.stdout.strip() or "git commit failed")

    push = _run_git(["push", config.remote, config.branch], repo_root)
    if push.returncode != 0:
        detail = (push.stderr or push.stdout or "").strip()
        raise PublishError(detail or "git push failed")

    return dest_file
