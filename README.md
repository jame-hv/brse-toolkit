# brse-toolkit

Claude Code plugin for day-to-day BrSE work: JP-VI translation, spec/code/Excel
cross-checking, report/slide/DD generation, Q&A management — with persistent
memory per project.

## Install

This repo is published on GitHub at `jame-hv/brse-toolkit`. `claude plugin
install` only resolves plugin names from registered marketplaces, so install
is 2 steps: register this repo as a marketplace, then install the plugin from
it. From inside a Claude Code session:

    /plugin marketplace add jame-hv/brse-toolkit
    /plugin install brse-toolkit@brse-toolkit

or from the shell:

    claude plugin marketplace add jame-hv/brse-toolkit
    claude plugin install brse-toolkit@brse-toolkit

(`brse-toolkit@brse-toolkit` = `<plugin-name>@<marketplace-name>` — same name
twice because this marketplace only holds this one plugin.)

Update after pulling new commits:

    claude plugin marketplace update brse-toolkit

## Starting a new project

Open Claude Code in the project (client/project) directory and run:

    /brse-toolkit:init

It asks a few questions (project name, languages, source and template folders,
deliverables), then creates `.brse/` (`config.json`, `memory/long/`,
`memory/short/`, `knowledge/docs/`), writes a project block into `CLAUDE.md`,
and runs `git init` if the folder isn't a git repo yet.

Settings merge in three layers, later wins: plugin defaults
(`config/defaults.json`) → your own `~/.config/brse-toolkit/config.json` →
the workspace's `.brse/config.json`. Check the result with
`python3 <plugin>/scripts/brse-config.py`. API keys never go in these files —
set them as environment variables and name the variable in the config
(e.g. `"api_key_env": "OPENAI_API_KEY"`). See
`docs/superpowers/specs/2026-08-02-brse-toolkit-design.md` in the source repo
for the full architecture.

## Commands

| Command | What it does |
|---|---|
| `/brse-toolkit:setup` | Installs what the plugin needs: Python packages into a private venv, optional tools only with your yes per item |
| `/brse-toolkit:doctor` | Shows which tools are available on this machine and what is missing (read-only) |
| `/brse-toolkit:init` | Sets up a workspace (`.brse/`), asks about the project, writes the project block of `CLAUDE.md` |
| `/brse-toolkit:ingest` | Converts client documents into searchable Markdown + an index, and lists what could not be read as text |
| `/brse-toolkit:memory-review` | Promotes settled facts and your corrections from session logs into long-term memory, with your approval per item |
| `/brse-toolkit:library` | Saves approved deliverables for reuse in other projects |

## How memory works

- **Session logs** (`.brse/memory/short/`) are written automatically by the
  plugin's `Stop` / `PreCompact` hooks: your requests, files written, the last
  reply. Nothing is summarised by a model; old logs are pruned after
  `memory.short_retention_days`.
- **Long-term memory** (`.brse/memory/long/`): parties, glossary, conventions,
  decisions, and a feedback log of your corrections by category. Written only
  with your approval (`/brse-toolkit:memory-review`, or when you confirm a fact).
- **At session start** a hook tells the agent the project, the active
  conventions, the most frequent corrections of the last 30 days, and what the
  previous session did.

## Optional providers

| Capability | Used when available | Otherwise |
|---|---|---|
| Second-agent review / back-translation | `codex`, `gemini` (signed in), or OpenAI API (`providers.openai.model` + key env var) | a Claude subagent, reported as not model-independent |
| Machine translation base layer | DeepL (`DEEPL_API_KEY`), OpenAI | Claude alone, reported as such |
| Office files | the office CLIs in `tools.office_order` | Python libraries |
| Diagrams | draw.io CLI (`.drawio` and Mermaid → PNG) | Mermaid text, not rendered |

API keys live in environment variables only; the config names the variable.

## Dependencies

    pip install -r requirements.txt        # plugin users: /brse-toolkit:setup does this for you
    pip install -r requirements-dev.txt    # developing this repo (adds pytest)

Also required on the machine: `ripgrep` (rg), `tesseract-ocr` + the `jpn`
language pack, and `libreoffice` (used as a fallback to render Excel sheets
that contain shapes/annotations to an image).

## Developing this repo directly (not as an installed plugin)

Every `SKILL.md` references its own scripts as `${CLAUDE_PLUGIN_ROOT}/skills/...`
— that variable is set automatically by Claude Code once this repo is
installed as a plugin (see Install above), but it is **not** set when you
just open this repo's own working directory in Claude Code to work on the
toolkit itself. In that case, resolve `${CLAUDE_PLUGIN_ROOT}` as this repo's
root manually — the paths are otherwise identical.

## Tests

    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q     # script + plugin-structure tests, free, writes no cache
    claude plugin validate .                           # manifest / skills / commands
    claude plugin eval . --runs 1                      # behavior evals in evals/ — runs real agents, costs API usage

`pytest.ini` turns off pytest's cache; `PYTHONDONTWRITEBYTECODE=1` stops `__pycache__/` folders from being written.
