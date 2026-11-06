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

## Trigger

Need to answer a question from the client or a dev — via a chat/ticket tool
(Backlog, Redmine, Chatwork...) or by writing into the answer column of an
Excel Q&A list.

## Before answering — mandatory

1. Read `.brse/memory/long/parties.md` — determine which party is asking, which party will
   read the answer. Apply the relay model: do NOT carry the original question's
   pronouns verbatim into the answer if the reader is a different party — use
   the specific party's name, or the neutral Vietnamese "chúng tôi"/"quý vị".
2. If the answer will be written into an existing Excel Q&A list file: run
   `<py> ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py
   <path/to/qa-list.xlsx>` to read back every existing question/answer.
3. Compare the new question against existing ones (simple text similarity — same
   intent, not necessarily same wording). If it matches a question already
   answered → return the existing answer, do NOT compose a different one on
   your own.

## Tone per channel

- **Chat/ticket tool**: concise, straight to the answer, moderate politeness
  level, no email-style opening/closing.
- **Excel Q&A list**: one notch more formal, since it's an official record.

Both channels share `.brse/memory/long/glossary.md` for terminology — don't invent new
wording.

## Batch processing (multiple independent units)

Multiple independent Q&A items in the same request (e.g. "answer these 10
questions in this Q&A list") → dispatch in parallel (spec section 11), one
subagent per question. Each subagent reads `.brse/memory/long/parties.md` +
`.brse/memory/long/glossary.md` itself before drafting. The main agent aggregates results,
dedupes newly-found terms/decisions, then asks the user once, and writes to the
Q&A list file in one pass. **Subagents never write to `.brse/memory/` themselves.**

## After answering

- An uncertain answer → label it as unconfirmed and needing to be asked to the client, in the reply language (the
  `verify-output` policy — run
  `${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on
  the draft before sending), don't guess at the client's intent.
- If this answer is a new decision not yet in `.brse/memory/long/decisions-log.md` → ask
  the user whether to save it, then write it immediately (don't delay — see the
  CLAUDE.md rule).
