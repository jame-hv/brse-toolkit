---
name: approach
description: Use this when the user needs a project approach / policy document (方針, アプローチ, 進め方) — e.g. an upgrade, migration, cutover or test approach — built from the source code and documents, with options weighed, a chosen approach, phases, roles, risks and the diagrams that explain it.
---

## Before running

`<py>` below = the Python recorded by `/brse-toolkit:setup` (`runtime.python`
in `~/.config/brse-toolkit/config.json` — read that file directly), else the
first of `python3`, `python`, `py -3` that runs. No Python at all → tell the
user to run `/brse-toolkit:setup`, and continue only with steps that need no
script, saying which checks were skipped.

Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py config` and read its JSON:
- `error` → show it to the user and stop; the config file must be fixed first.
- `workspace_root` is null → the folder isn't initialized. Ask once: run
  `/brse-toolkit:init` first (recommended — memory and knowledge get saved for
  next time) or continue once without saving. Running as a subagent dispatched
  by a main agent → the parent already resolved this; proceed.
- Otherwise use `config.paths` (`sources`, `templates`, `outputs` — relative to
  `workspace_root`), `config.style`, `config.translation`, and the files in
  `.brse/memory/long/`. Never assume a folder name the config doesn't list.
- `warnings` not empty → mention them in one line (likely a typo in the config).

## When to use

"Draft the 方針 / approach for X" — version-up, migration, cutover, test
strategy, operation handover. The approach must be argued from the sources,
not from general best practice.

## Steps

1. **Restate**: goal, reader (client / internal), decisions already made
   (`.brse/memory/long/decisions-log.md`), constraints (budget, dates, who
   does what), format (slides via `report-gen`, or a document).
2. **Facts first.** From the code: run `code-to-business` / an inventory of
   the system (entry points, batches and schedules, queues, external
   integrations, storage, environments, framework and library versions — each
   with `file:line`). From documents: `brse.py kb-search` then read. Write the fact
   base as a list; every later statement must point into it.
3. **Options.** 2–3 real alternatives for each key choice (e.g. big-bang vs
   phased, who executes cutover, test method), each with effort, risk, what
   the client must do, and how it fits the constraints. Use
   `brainstorm-brse` for the format. Recommend one per choice, with the
   deciding reason.
4. **Approach document**, in this order: 目的 · 前提・制約 · 対象範囲 (in / out)
   · 方式 (chosen options + why) · 進め方 (phases with entry/exit criteria and
   gates) · 体制・役割 (client / us, RACI-style) · 成果物 · リスクと対策 ·
   確認事項. Short statements, one idea each; no durations or dates the user
   has not approved.
5. **Diagrams** with the `diagram` skill: current system, target system, and
   the process (phases or cutover steps), each starting from a draw.io
   template and checked with `brse.py drawio-tool lint`. The same names in the
   diagrams and in the text.
6. Do not start implementing or a PoC.

## Output

The document/deck path, the fact base with refs, the options table with the
chosen ones, the diagrams, open questions. Then `review-gate`
(`brse.py verify-claims` on the fact base, rubric judge on the whole).
