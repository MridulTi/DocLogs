# DocLogs Roadmap

Phases and todos for building the DocLogs CLI. Update checkboxes as work completes.

**Current focus:** Phase 2 — weekly review

**Living change log:** `.cursor/skills/doclogs/changes.md` (append decisions and completed work there)

---

## Phase 0 — Fix the skeleton ✅

**Goal:** `doclog --help` works; all five commands run without crashing.

| # | Task | Status |
|---|------|--------|
| 0.1 | Fix `main.py` — `importlib`, `COMMANDS_DIR` via `.resolve().parent` | ✅ |
| 0.2 | Fix `commands/config.py` — add `import yaml` | ✅ |
| 0.3 | Fix `requirements.txt` — add PyYAML; remove `pathlib`, `typing` backports | ⬜ optional |
| 0.4 | Configure `pyproject.toml` — setuptools packages + `doclog` entry point | ✅ |
| 0.5 | Create storage dirs — `doclog/entries/`, `doclog/posts/`, `doclog/cache/` + `.gitkeep` | ✅ |
| 0.6 | Install & verify — `pip install -e .`, `doclog --help` | ✅ |
| 0.7 | Smoke-test all commands — capture, weekly, generate, sanitize, config | ✅ |

---

## Phase 1 — Capture ✅

**Goal:** `doclog capture` writes a real daily YAML file with git evidence; re-runs merge instead of wipe.

| # | Task | Status |
|---|------|--------|
| 1.1 | Define daily entry YAML schema in `helper/entry.py` | ✅ |
| 1.2 | Git collector — repo path, branch, today's commits (`helper/git_collector.py`) | ✅ |
| 1.3 | Idempotent capture — load + merge notes, refresh git (`helper/capture.py`) | ✅ |
| 1.4 | Warn when not inside a git repo (`commands/capture.py`) | ✅ |

**Entry file:** `doclog/entries/YYYY-MM-DD.yaml`

**Deferred (later):**
- `--include-terminal` — terminal history evidence
- `--include-tickets` — ticket / issue IDs
- `--repo` flag — capture from a specific repo path

---

## Phase 2 — Weekly review

**Goal:** `doclog weekly` reads real entries and surfaces story candidates (no hardcoded stubs).

| # | Task | Status |
|---|------|--------|
| 2.1 | Load last N days from `doclog/entries/` (`helper/weekly.py`) | ⬜ |
| 2.2 | Build story candidates from commit subjects + note lines | ⬜ |
| 2.3 | Wire `commands/weekly.py` — `--days`, `--limit`, empty-state messages | ⬜ |
| 2.4 | Smarter ranking — prefer notes, boost high-activity days | ⬜ |

---

## Phase 3 — Sanitize

**Goal:** Redact sensitive content before any LLM call.

| # | Task | Status |
|---|------|--------|
| 3.1 | Redact internal URLs, IPs, tokens, API keys (`helper/sanitize.py`) | ⬜ |
| 3.2 | Flag suspicious content for review | ⬜ |
| 3.3 | Wire `commands/sanitize.py` — read from entry file or stdin | ⬜ |
| 3.4 | Pipe sanitize into generate flow (Phase 4 dependency) | ⬜ |

---

## Phase 4 — Generate

**Goal:** `doclog generate <type>` produces markdown artifacts from captured stories.

| # | Task | Status |
|---|------|--------|
| 4.1 | Load prompt templates from `prompts/` (blog, linkedin, resume) | ⬜ |
| 4.2 | Provider adapter interface — read `config.yaml` (openai, ollama, …) | ⬜ |
| 4.3 | Implement one provider first (Ollama local recommended) | ⬜ |
| 4.4 | Wire `commands/generate.py` — pick story → sanitize → prompt → write `doclog/posts/` | ⬜ |
| 4.5 | Add remaining providers (OpenAI, Anthropic, Gemini) | ⬜ |

---

## Phase 5 — Polish

**Goal:** Production-ready UX, docs, and hygiene.

| # | Task | Status |
|---|------|--------|
| 5.1 | `doclog config show|set` improvements | ⬜ |
| 5.2 | Scheduler docs — cron / launchd examples (no built-in scheduler) | ⬜ |
| 5.3 | Tests — sanitize, YAML I/O, git collector | ⬜ |
| 5.4 | README walkthrough with real `capture → weekly → generate` flow | ⬜ |
| 5.5 | Clean up duplicate imports in `helper/entry.py` | ⬜ |
| 5.6 | Clean up duplicate imports in `helper/entry.py` | ⬜ |

---

## Build order (do not skip)

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5
 skeleton     capture      weekly     sanitize    generate    polish
```

**Rule:** Capture first, publish later. Do not wire LLM providers before sanitize works.

---

## Repo layout (current)

```
./
├── main.py
├── config.yaml
├── commands/          # CLI command registrations
│   ├── capture.py
│   ├── weekly.py
│   ├── generate.py
│   ├── sanitize.py
│   └── config.py
├── helper/            # shared logic
│   ├── entry.py       # schema, load/save YAML
│   ├── git_collector.py
│   └── capture.py     # build_capture_entry (merge + git)
├── doclog/
│   ├── entries/       # daily capture YAML
│   ├── posts/         # generated artifacts
│   └── cache/
├── prompts/
└── docs/
    ├── vision.md
    ├── architecture.md
    └── roadmap.md     # this file
```

---

## How to work with the DocLogs skill

1. Read this roadmap for what is next.
2. Append progress to `.cursor/skills/doclogs/changes.md`.
3. Invoke `@DocLogs` for suggest-only code (you apply changes yourself).
