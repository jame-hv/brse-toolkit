---
name: qa-tone-brse
description: Use this when the user needs to answer a question from a client or dev — via a chat/ticket tool (Backlog, Redmine, Chatwork...) or an Excel Q&A list — in the right tone for that channel. Also manages the QA log directly inside the Excel file sent to the client.
---

## Before running

`<py>` below = the Python recorded by `/brse-toolkit:setup` (`runtime.python`
in `~/.config/brse-toolkit/config.json` — read that file directly), else the
first of `python3`, `python`, `py -3` that runs. No Python at all → tell the
user to run `/brse-toolkit:setup`, and continue only with steps that need no
script, saying which checks were skipped.

Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse-config.py` and read its JSON:
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

A question from the client or a developer must be answered — in a chat/ticket
tool (Backlog, Redmine, Chatwork, ...) or in the answer column of an Excel
Q&A list.

## Steps

1. **Understand the question.** Re-read it: what exactly is asked (a yes/no,
   a value, a decision, a schedule)? One message with several questions →
   split them and answer each, numbered the same way.
2. **Who asks, who reads** — `.brse/memory/long/parties.md`. Relay model: the
   asker's pronouns are not carried into the answer when the reader is a
   different party; use the party's name, or the neutral form of the reply
   language.
3. **Already answered?** Q&A list in Excel → read every existing row with
   `<py> ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py <qa-list.xlsx>`.
   Same intent as an answered question → reuse that answer and cite its No.,
   don't compose a different one.
4. **Find the answer in the sources** (spec, design, code via
   `code-to-business`, decisions-log). Cite it. Not found → the answer says
   it is unconfirmed and what will be checked, never a guess at the client's
   intent.
5. **Write**:
   - First sentence answers directly (yes / no / the value / the decision).
   - Then the reason or condition, then what is needed from the reader, if
     anything.
   - Roughly as long as the question — not an essay.
   - Terms from `.brse/memory/long/glossary.md`; don't coin new wording.
6. **Excel Q&A list**: write into a copy (never the original), only in the
   answer / status / date columns, keeping the sheet's formatting and row
   structure. List the cells written.

## Tone per channel

- **Chat / ticket**: concise, straight to the answer, moderate politeness, no
  email-style opening or closing.
- **Excel Q&A list**: one notch more formal — it is an official record.

## Batch processing

Several independent questions → one subagent per question (spec section 11),
each reading `parties.md` + `glossary.md` itself. The main agent merges,
dedupes new terms/decisions, asks the user once, and writes the Q&A file in
one pass. **Subagents never write to `.brse/memory/` themselves.**

## After answering

- An answer that is a new decision → ask whether to record it in
  `.brse/memory/long/decisions-log.md`; write it immediately on a yes.
- Run `verify-output` on the draft.
