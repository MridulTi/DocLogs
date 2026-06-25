# DevLogs

DevLogs is an engineer career operating system for capturing and reusing technical work.

## What it solves

Engineers do valuable work every day: incident response, CI/CD and platform debugging, automation, infrastructure changes, PR reviews, and migrations. Most of that work is forgotten when it matters most: performance reviews, promotion packets, interviews, and professional storytelling.

DevLogs helps you turn day-to-day engineering activity into durable artifacts by:

- capturing evidence automatically from git, branches, PRs, and optional histories
- summarizing weekly progress and surfacing strong stories
- generating markdown artifacts for blog posts, LinkedIn, resumes, and interview prep
- keeping model usage provider-agnostic and safe with sanitization

## Core commands

- `devlog capture`
  - collect commits, repository activity, PR titles, tickets, and optional notes
  - store structured daily entries in local storage
- `devlog weekly`
  - review weekly work
  - surface candidate stories worth expanding
- `devlog generate <type>`
  - create reusable artifacts such as `blog`, `linkedin`, `resume`, `interview`, or `changelog`
- `devlog sanitize`
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
├── devlog/
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

DevLogs keeps the capture layer local and the generation layer model-agnostic. It is intentionally not a scheduler; use OS-level schedulers like `cron`, `systemd --user`, `launchd`, or Task Scheduler to invoke `devlog capture` at reminder times.

For implementation, start by focusing on:

1. evidence collection and local storage
2. weekly summaries and story selection
3. safe prompt generation
4. provider adapters for OpenAI, Ollama, Anthropic, Gemini, or other APIs

## Getting started

1. Configure `config.yaml` with your preferred LLM provider.
2. Add a scheduler entry outside the CLI to invoke `devlog capture` at your preferred check-in time.
3. Capture daily progress and generate reusable career artifacts from the same captured story.
