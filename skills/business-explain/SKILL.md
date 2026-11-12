---
name: business-explain
description: Use this when a feature, screen or business flow must be explained to someone who does not know the system — a new member, a manager, a sales person or a non-technical client — in plain words, from the project's documents (doc-to-md output) and/or code, with every statement traceable to its source.
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

"Explain what this feature does", onboarding a new member, a summary for a
manager or client who doesn't read specs. For a technical explanation from
code for developers, use `code-to-business`.

## Steps

1. **Reader first.** Pick one: non-tech (client/manager/sales), new member
   (knows software, not this system), new developer. State it at the top;
   it decides vocabulary and depth. Output language from the request or config.
2. **Collect facts with sources.** Read `.brse/knowledge/docs/` (run `doc-to-md`
   first if missing); for behaviour only visible in code, run
   `code-to-business` and reuse its cited facts. Every fact keeps its source
   (file + sheet/heading/row, or file:line). Gaps → "cần xác nhận / 要確認",
   never filled by guessing.
3. **Write in this order** (draft facts only — wording is done by Comtor):
   1. *In one sentence*: what it is for and who uses it.
   2. *Why it exists*: the business problem it solves.
   3. *Who and when*: roles, triggers, frequency.
   4. *Step by step*: the business flow in plain words, one action per step,
      no field IDs or table names for non-tech readers.
   5. *A real-life example*: one concrete scenario with sample values from
      the spec (say they are examples).
   6. *Rules that matter*: limits, validations, statuses, what is blocked
      and why — as "if … then …".
   7. *Glossary*: every term the reader would trip on → plain meaning
      (project glossary first).
   8. *FAQ / what to watch out for* and the open questions.
   Optional: a simple flow diagram (ask System Engineer, `diagram` skill,
   `flow` or `flow-lanes` type) — at most ~10 boxes for non-tech readers.
4. **Plain-language check**: no sentence over ~25 words for non-tech; no
   unexplained acronym; no screen/table/variable names unless the reader is a
   developer. Every paragraph still has its source tag.
5. **Wording**: send the draft + sources + reader + language to Comtor;
   check back that no fact, number or rule changed meaning.

## Output

The explanation (Markdown, or Word/Slide via `report-gen` when asked),
saved in `config.paths.outputs`, with the source list at the end and the
open questions inline in the reply.

## Handoff

Finish with `review-gate` (runs `verify-output`).
