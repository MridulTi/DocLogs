# DocLogs Change Log

Living record of what is being built, changed, or decided in this repo. The DocLogs skill reads this file in full on every invocation to stay current.

Append new entries at the bottom. Keep older entries—do not delete history.

---

### 2026-06-25 — done

**Area:** docs

**Summary:** Added Cursor project instructions and DocLogs suggest-only skill

**Details:**
- Created `.cursor/rules/repository.mdc` — repository instructions (mirrors `.copilot` for Cursor)
- Created `.cursor/skills/doclogs/SKILL.md` — suggest-only advisor skill
- Created this `changes.md` as the shared change log for project context
- Skill reads the full log before responding; user appends new entries manually

### 2026-06-25 — done

**Area:** cli

**Summary:** Phase 0 complete — `doclog` runs end to end

**Details:**
- 0.1 Fixed `main.py`: `importlib`, `COMMANDS_DIR` via `.resolve().parent`
- 0.2 Fixed `commands/config.py`: added `import yaml`
- 0.3 Updated `requirements.txt`: added PyYAML (optional: remove `pathlib`, `typing`)
- 0.4 Configured `pyproject.toml`: setuptools `py-modules` + `commands` package discovery
- 0.5 Created `doclog/entries/`, `doclog/posts/`, `doclog/cache/` with `.gitkeep`
- 0.6 Verified `pip install -e .` and `doclog --help`
- 0.7 Smoke-tested: capture, weekly, generate, sanitize, config — all pass

**Files touched:** `main.py`, `commands/config.py`, `requirements.txt`, `pyproject.toml`, `.gitignore`, `doclog/**/.gitkeep`

---

### 2026-06-25 — done

**Area:** capture

**Summary:** Phase 1.1 — daily entry YAML schema

**Details:**
- Added `commands/entry.py`
- `capture` writes `doclog/entries/YYYY-MM-DD.yaml`

---

### 2026-06-25 — in-progress

**Area:** capture

**Summary:** Phase 1.2 — git collector

**Details:**
- Added `commands/git_collector.py`
- Fills repository path, branch, today's commits
- Wired into `capture`

---

### 2026-06-25 — done

**Area:** generate

**Summary:** IDE-native post generation via Cursor and Copilot CLI

**Details:**
- Added `helper/llm/` provider layer: `prompt_only`, `cursor`, `copilot`
- `doclog generate` supports `--provider`, `--prompt-only`, `--force`
- Default remains `prompt_only`; opt in via `~/.doclog/config.yaml`
- External providers write `{slug}-{type}-prompt.md` and `{slug}-{type}.md`
- `doclog config` shows provider availability for Cursor and Copilot CLIs
- Updated `helper/templates/config.yaml`, README, architecture, roadmap

**Files touched:** `helper/llm/*`, `helper/generate.py`, `commands/generate.py`, `commands/config.py`, `helper/paths.py`, docs