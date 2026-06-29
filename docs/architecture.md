# Architecture

DocLogs is designed as a local operating system for engineering accomplishments, with a lightweight CLI capturing evidence and a model-agnostic generation layer.

## High-level flow

1. `doclog capture`
   - collects local evidence from git, branches, PRs, and optionally terminal history or ticket IDs
   - stores daily entries in structured files under `doclog/entries`
2. `doclog weekly`
   - summarizes recent updates and surfaces candidate stories
   - helps the user pick what to expand into a durable artifact
3. `doclog generate <type>`
   - asks a few targeted questions about the chosen story
   - produces Markdown artifacts such as `posts/*.md`, `linkedin.md`, and `resume_bullet.md`
4. `doclog sanitize`
   - applies a safety filter before any LLM call
   - removes internal URLs, secrets, account IDs, IP addresses, and customer data
   - flags suspicious content for review rather than sending it blindly

## Storage layout

- `doclog/entries/`
  - daily capture files, e.g. `2026-06-21.yaml`
- `doclog/posts/`
  - generated markdown artifacts for stories
- `doclog/cache/`
  - temporary state, extracted metadata, or API caches
- `config.yaml`
  - user-configurable provider and prompt defaults
- `prompts/`
  - target artifact prompt templates such as `blog.md`, `linkedin.md`, `resume.md`

## Model-agnostic provider support

The config file allows users to select a provider and associated settings. By default, `doclog generate` writes a sanitized prompt file only (`prompt_only`). Opt in to IDE-native providers that reuse existing logins on your machine:

- **cursor** — Cursor CLI (`agent login`)
- **copilot** — GitHub Copilot CLI (`copilot`)

API-based providers (OpenAI, Ollama, Anthropic, Gemini) are planned for a later phase.

Example:

```yaml
llm:
  provider: prompt_only

cursor:
  command: agent
  model: auto
  mode: ask
  timeout_seconds: 120

copilot:
  command: copilot
  model: auto
  timeout_seconds: 120
```

The CLI routes generation through `helper/llm/` adapters and never hard-codes a single provider.

## Sanitization layer

Before any text is sent to a model, DocLogs should:

- remove or redact company names and internal hostnames
- strip internal URLs and private IP addresses
- redact secrets, tokens, and credentials
- remove account IDs and sensitive metadata
- surface a review step if content appears suspicious

This protects the user from accidentally sending private infrastructure details to an external provider.

## Scheduler separation

DocLogs is a capture tool, not a scheduler.

- The CLI should provide a `remind` or `capture` command, but not own timed execution.
- Users can integrate with OS-level schedulers like `cron`, `systemd --user`, `launchd`, or Windows Task Scheduler.
- This keeps the CLI simple and reliable while still supporting notification-driven workflows.

## Recommended file structure

```
./
├── README.md
├── config.yaml
├── docs/
│   ├── vision.md
│   └── architecture.md
├── doclog/
│   ├── entries/
│   ├── posts/
│   ├── cache/
│   └── prompts/
└── .copilot
```
