# Architecture

DocLogs is designed as a local operating system for engineering accomplishments, with a lightweight CLI capturing evidence and a model-agnostic generation layer.

## High-level flow

1. `devlog capture`
   - collects local evidence from git, branches, PRs, and optionally terminal history or ticket IDs
   - stores daily entries in structured files under `devlog/entries`
2. `devlog weekly`
   - summarizes recent updates and surfaces candidate stories
   - helps the user pick what to expand into a durable artifact
3. `devlog generate <type>`
   - asks a few targeted questions about the chosen story
   - produces Markdown artifacts such as `posts/*.md`, `linkedin.md`, and `resume_bullet.md`
4. `devlog sanitize`
   - applies a safety filter before any LLM call
   - removes internal URLs, secrets, account IDs, IP addresses, and customer data
   - flags suspicious content for review rather than sending it blindly

## Storage layout

- `devlog/entries/`
  - daily capture files, e.g. `2026-06-21.yaml`
- `devlog/posts/`
  - generated markdown artifacts for stories
- `devlog/cache/`
  - temporary state, extracted metadata, or API caches
- `config.yaml`
  - user-configurable provider and prompt defaults
- `prompts/`
  - target artifact prompt templates such as `blog.md`, `linkedin.md`, `resume.md`

## Model-agnostic provider support

The config file should allow users to select a provider and associated settings.

Example:

```yaml
llm:
  provider: openai
  openai:
    model: gpt-4o-mini
    api_key: ${OPENAI_API_KEY}
  ollama:
    endpoint: http://localhost:11434
  anthropic:
    model: claude-3
  gemini:
    model: gemini-pro
```

The CLI should route generation through an adapter layer and never hard-code a single provider.

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
├── devlog/
│   ├── entries/
│   ├── posts/
│   ├── cache/
│   └── prompts/
└── .copilot
```
