from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from helper.git_collector import find_git_root
from helper.llm.config import load_raw_config, save_config
from helper.paths import posts_dir, publish_repos_dir

PUBLISH_KEYS = frozenset({"repo", "branch", "remote", "subdir"})

_GIT_SSH_RE = re.compile(r"^git@([^:]+):(.+?)(?:\.git)?/?$")
_GITHUB_HTTPS_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


@dataclass
class PublishConfig:
    repo_path: Path | None
    repo_url: str | None = None
    branch: str = "main"
    remote: str = "origin"
    subdir: str = "posts"


@dataclass
class ResolvedRepo:
    path: Path
    remote_url: str | None = None
    action: str = "configured"


class PublishError(RuntimeError):
    pass


def is_git_remote_url(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith(("https://", "http://", "ssh://", "git://")):
        return True
    return bool(_GIT_SSH_RE.match(stripped))


def repo_slug_from_url(url: str) -> str:
    stripped = url.strip().rstrip("/")
    ssh_match = _GIT_SSH_RE.match(stripped)
    if ssh_match:
        owner, repo = ssh_match.groups()
        return f"{owner}-{repo.replace('.git', '')}"

    https_match = _GITHUB_HTTPS_RE.match(stripped)
    if https_match:
        owner, repo = https_match.groups()
        return f"{owner}-{repo.replace('.git', '')}"

    parsed = urlparse(stripped)
    if parsed.path:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            return f"{parts[-2]}-{parts[-1].replace('.git', '')}"

    safe = re.sub(r"[^\w.-]+", "-", stripped).strip("-")
    return safe or "repo"


def resolve_publish_repo(value: str) -> ResolvedRepo:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Repo value cannot be empty.")

    if is_git_remote_url(stripped):
        remote_url = stripped
        slug = repo_slug_from_url(remote_url)
        dest = publish_repos_dir() / slug

        if dest.exists() and find_git_root(dest) is not None:
            pull = _run_git(["pull", "--ff-only"], dest)
            if pull.returncode != 0:
                detail = (pull.stderr or pull.stdout or "").strip()
                raise ValueError(f"Could not update clone at {dest}: {detail or 'git pull failed'}")
            return ResolvedRepo(path=dest.resolve(), remote_url=remote_url, action="updated")

        if dest.exists():
            raise ValueError(
                f"Path exists but is not a git repo: {dest}. Remove it or choose another URL."
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        clone = subprocess.run(
            ["git", "clone", remote_url, str(dest)],
            capture_output=True,
            text=True,
            check=False,
        )
        if clone.returncode != 0:
            detail = (clone.stderr or clone.stdout or "").strip()
            raise ValueError(f"git clone failed: {detail or 'unknown error'}")

        repo_root = find_git_root(dest)
        if repo_root is None:
            raise ValueError(f"Clone succeeded but directory is not a git repo: {dest}")

        return ResolvedRepo(path=repo_root.resolve(), remote_url=remote_url, action="cloned")

    repo_path = Path(stripped).expanduser()
    if not repo_path.is_absolute():
        repo_path = repo_path.resolve()
    else:
        repo_path = repo_path.resolve()

    if not repo_path.exists():
        raise ValueError(
            f"Repo path does not exist: {repo_path}\n"
            "Use a local clone path, or pass a git URL such as "
            "https://github.com/MridulTi/DocLogs"
        )

    repo_root = find_git_root(repo_path)
    if repo_root is None:
        raise ValueError(f"Not a git repository: {repo_path}")

    return ResolvedRepo(path=repo_root.resolve(), remote_url=None, action="configured")


def publish_config_from_settings(settings: dict[str, object]) -> PublishConfig:
    section = settings.get("publish", {})
    if not isinstance(section, dict):
        section = {}

    repo_raw = section.get("repo")
    repo_path = None
    if isinstance(repo_raw, str) and repo_raw.strip():
        repo_path = Path(repo_raw).expanduser().resolve()

    repo_url = section.get("repo_url")
    repo_url_str = repo_url.strip() if isinstance(repo_url, str) and repo_url.strip() else None

    branch = section.get("branch", "main")
    remote = section.get("remote", "origin")
    subdir = section.get("subdir", "posts")

    return PublishConfig(
        repo_path=repo_path,
        repo_url=repo_url_str,
        branch=str(branch) if branch else "main",
        remote=str(remote) if remote else "origin",
        subdir=str(subdir) if subdir else "posts",
    )


def load_publish_config(path: Path | None = None) -> PublishConfig:
    _, settings = load_raw_config(path)
    return publish_config_from_settings(settings)


def set_publish_value(key: str, value: str, path: Path | None = None) -> tuple[Path, ResolvedRepo | None]:
    normalized = key.strip().lower()
    if normalized not in PUBLISH_KEYS:
        allowed = ", ".join(sorted(PUBLISH_KEYS))
        raise ValueError(f"Unknown publish setting {key!r}. Choose one of: {allowed}")

    config_file, settings = load_raw_config(path)
    publish = settings.get("publish")
    if not isinstance(publish, dict):
        publish = {}
        settings["publish"] = publish

    resolved: ResolvedRepo | None = None
    if normalized == "repo":
        resolved = resolve_publish_repo(value)
        publish["repo"] = str(resolved.path)
        if resolved.remote_url:
            publish["repo_url"] = resolved.remote_url
        else:
            publish.pop("repo_url", None)
        current_branch = publish.get("branch", "main")
        subdir = publish.get("subdir", "posts")
        if not current_branch or str(current_branch).strip() == str(subdir).strip():
            publish["branch"] = detect_default_branch(resolved.path)
    else:
        publish[normalized] = value.strip()

    return save_config(settings, config_file), resolved


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


def detect_default_branch(repo_root: Path) -> str:
    remote_head = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], repo_root)
    if remote_head.returncode == 0:
        return remote_head.stdout.strip().rsplit("/", 1)[-1]

    current = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if current.returncode == 0:
        name = current.stdout.strip()
        if name and name != "HEAD":
            return name

    return "main"


def _validate_publish_branch(config: PublishConfig, repo_root: Path) -> str:
    branch = config.branch.strip()
    subdir = config.subdir.strip()

    if branch == subdir:
        detected = detect_default_branch(repo_root)
        raise PublishError(
            f"publish.branch is {branch!r} but that matches subdir (folder name), not a git branch.\n"
            f"Run: doclog publish set branch {detected}\n"
            f"subdir {subdir!r} is where posts are copied inside the repo."
        )

    return branch


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
            "Publish repo is not configured. Run:\n"
            "  doclog publish set repo ~/projects/my-blog\n"
            "  doclog publish set repo https://github.com/MridulTi/DocLogs"
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

    branch = _validate_publish_branch(config, repo_root)
    push = _run_git(["push", config.remote, f"HEAD:{branch}"], repo_root)
    if push.returncode != 0:
        detail = (push.stderr or push.stdout or "").strip()
        if "src refspec" in detail and branch in detail:
            detected = detect_default_branch(repo_root)
            raise PublishError(
                f"{detail}\n"
                f"Hint: branch {branch!r} is not valid. Run: doclog publish set branch {detected}"
            )
        raise PublishError(detail or "git push failed")

    return dest_file
