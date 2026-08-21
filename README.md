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

This creates `documents/`, `templates/`, `memory/`, `CLAUDE.md` in the current
directory, and runs `git init` if it isn't already a git repo. See
`docs/superpowers/specs/2026-08-02-brse-toolkit-design.md` in the source repo
for the full architecture.

## Dependencies

    pip install -r requirements.txt

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
