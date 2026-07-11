# DocLogs

DocLogs is an engineer career operating system for capturing and reusing technical work.

## What it solves

Engineers do valuable work every day: incident response, CI/CD and platform debugging, automation, infrastructure changes, PR reviews, and migrations. Most of that work is forgotten when it matters most: performance reviews, promotion packets, interviews, and professional storytelling.

DocLogs helps you turn day-to-day engineering activity into durable artifacts by:

- capturing evidence automatically from git, branches, PRs, and optional histories
- summarizing weekly progress and surfacing strong stories
- generating markdown artifacts for blog posts, LinkedIn, resumes, and interview prep
- keeping model usage provider-agnostic and safe with sanitization

Use `--syntax` on any command for usage, options, and examples (e.g. `doclog generate --syntax`). Standard `--help` is also available.

## Core commands

- `doclog capture`
  - collect commits, repository activity, PR titles, tickets, and optional notes
  - store structured daily entries in local storage
- `doclog weekly`
  - review weekly work
  - surface candidate stories worth expanding
- `doclog generate <type>`
  - create reusable artifacts such as `blog`, `linkedin`, `resume`, `interview`, or `changelog`
  - default: saves a sanitized prompt file for manual use in Cursor or Copilot
  - optional: auto-generate via logged-in Cursor CLI or GitHub Copilot CLI
- `doclog sanitize`
  - sanitize captured content before any LLM request
  - redact internal URLs, tokens, IP addresses, and other sensitive details
- `doclog publish`
  - configure a git repo for publishing generated posts
  - commit and push a post to that repo

## Recommended repository structure

```
./
├── README.md
├── config.yaml
├── commands/
│   ├── capture.py
│   └── config.py
├── docs/
│   ├── vision.md
│   └── architecture.md
├── doclog/
│   ├── entries/
│   ├── posts/
│   └── cache/
├── prompts/
│   ├── blog.md
│   ├── linkedin.md
│   └── resume.md
```

## Architecture overview

DocLogs keeps the capture layer local and the generation layer model-agnostic. It is intentionally not a scheduler; use OS-level schedulers like `cron`, `systemd --user`, `launchd`, or Task Scheduler to invoke `doclog capture` at reminder times.

For implementation, start by focusing on:

1. evidence collection and local storage
2. weekly summaries and story selection
3. safe prompt generation
4. provider adapters for IDE CLIs (Cursor, Copilot) and optional API providers

## Getting started

### Install from PyPI

```bash
pip install -U doclogs-cli==0.1.8
doclog --help
```

### Install from source (development)

```bash
git clone https://github.com/MridulTi/DocLogs.git
cd DocLogs
python -m venv .venv
source .venv/bin/activate
pip install -e .
doclog --help
```

### First run

Data is stored under `~/.doclog/` (entries, posts, config). On first use, a default `config.yaml` is created there.

To keep using a project-local folder instead:

```bash
export DOCLOG_HOME="$PWD/doclog"
doclog capture
```

### Daily use

1. Configure `~/.doclog/config.yaml` (created automatically on first run).
2. Add a scheduler entry outside the CLI to invoke `doclog capture` at your preferred check-in time.
3. Capture daily progress and generate reusable career artifacts from the same captured story.

### Generate posts

```bash
# Default: prompt file only (paste into Cursor/Copilot chat manually)
doclog weekly
doclog generate blog -t "nginx fix"

# Auto-generate via logged-in Cursor CLI
doclog config set provider cursor
doclog generate blog -t "nginx fix"

# Or Copilot
doclog config set provider copilot

# Back to prompt-only
doclog config set provider prompt_only

# Check provider availability
doclog config
```

Ensure Cursor/Copilot CLI is installed and authenticated when using those providers (`agent login` or `copilot`).

### Publish a post to git

Point DocLogs at a local clone of your blog/docs repo, then commit and push generated posts:

```bash
doclog publish set repo ~/projects/my-blog
# or clone from GitHub automatically:
doclog publish set repo https://github.com/MridulTi/DocLogs
doclog publish set branch main
doclog generate blog -t 1
doclog publish push --latest
```

Or push a specific file:

```bash
doclog publish push ~/.doclog/posts/nginx-fix-blog.md -m "Add nginx TLS post"
```

## Publish to PyPI (GitHub Actions)

Publishing runs via GitHub Actions — no local `twine upload` needed.

1. Configure [trusted publishing](docs/publishing.md) on PyPI (leave Environment blank)
2. Push a version tag:

```bash
git tag v0.1.8
git push origin v0.1.8
```

The workflow uploads to PyPI automatically.

See [docs/publishing.md](docs/publishing.md) for full setup.
