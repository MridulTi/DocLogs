# DocLogs

DocLogs is an engineer career operating system for capturing and reusing technical work.

## What it solves

Engineers do valuable work every day: incident response, CI/CD and platform debugging, automation, infrastructure changes, PR reviews, and migrations. Most of that work is forgotten when it matters most: performance reviews, promotion packets, interviews, and professional storytelling.

DocLogs helps you turn day-to-day engineering activity into durable artifacts by:

- capturing evidence automatically from git, branches, PRs, and optional histories
- summarizing weekly progress and surfacing strong stories
- generating markdown artifacts for blog posts, LinkedIn, resumes, and interview prep
- keeping model usage provider-agnostic and safe with sanitization

## Core commands

- `doclog capture`
  - collect commits, repository activity, PR titles, tickets, and optional notes
  - store structured daily entries in local storage
- `doclog weekly`
  - review weekly work
  - surface candidate stories worth expanding
- `doclog generate <type>`
  - create reusable artifacts such as `blog`, `linkedin`, `resume`, `interview`, or `changelog`
- `doclog sanitize`
  - sanitize captured content before any LLM request
  - redact internal URLs, tokens, IP addresses, and other sensitive details

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
└── .copilot
```

## Architecture overview

DocLogs keeps the capture layer local and the generation layer model-agnostic. It is intentionally not a scheduler; use OS-level schedulers like `cron`, `systemd --user`, `launchd`, or Task Scheduler to invoke `doclog capture` at reminder times.

For implementation, start by focusing on:

1. evidence collection and local storage
2. weekly summaries and story selection
3. safe prompt generation
4. provider adapters for OpenAI, Ollama, Anthropic, Gemini, or other APIs

## Getting started

### Install from PyPI

```bash
pip install doclogs-cli
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

1. Configure `~/.doclog/config.yaml` with your preferred LLM provider (created automatically on first run).
2. Add a scheduler entry outside the CLI to invoke `doclog capture` at your preferred check-in time.
3. Capture daily progress and generate reusable career artifacts from the same captured story.

## Publish to PyPI (GitHub Actions)

Publishing runs via GitHub Actions — no local `twine upload` needed.

1. Configure [trusted publishing](docs/publishing.md) on PyPI (leave Environment blank)
2. Push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow uploads to PyPI automatically.

See [docs/publishing.md](docs/publishing.md) for full setup.
