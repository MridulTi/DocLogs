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

**Summary:** Phase 0 complete — `docklog` runs end to end

**Details:**
- 0.1 Fixed `main.py`: `importlib`, `COMMANDS_DIR` via `.resolve().parent`
- 0.2 Fixed `commands/config.py`: added `import yaml`
- 0.3 Updated `requirements.txt`: added PyYAML (optional: remove `pathlib`, `typing`)
- 0.4 Configured `pyproject.toml`: setuptools `py-modules` + `commands` package discovery
- 0.5 Created `devlog/entries/`, `devlog/posts/`, `devlog/cache/` with `.gitkeep`
- 0.6 Verified `pip install -e .` and `docklog --help`
- 0.7 Smoke-tested: capture, weekly, generate, sanitize, config — all pass

**Files touched:** `main.py`, `commands/config.py`, `requirements.txt`, `pyproject.toml`, `.gitignore`, `devlog/**/.gitkeep`

---

### 2026-06-25 — planned

**Area:** capture

**Summary:** Phase 1.1 — define daily entry YAML schema

**Details:**
- Schema for `devlog/entries/YYYY-MM-DD.yaml`
- Fields: date, git commits, branch, manual notes, captured_at
- No git collector yet — schema + write empty/sample file first