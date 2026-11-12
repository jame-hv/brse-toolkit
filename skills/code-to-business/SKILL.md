---
name: code-to-business
description: Use this when the user needs business logic explained or documented from existing, undocumented source code for one concrete feature/flow — never "the whole codebase". Every output sentence cites an exact file:line via brse.py extract-refs.
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

Business logic must be explained or documented from existing source code for
one concrete feature or flow (e.g. "order registration", "monthly closing
batch"). Never "the whole codebase" — scope unclear → ask, don't pick one.

## Steps (spec section 6.10)

0. If the project already has a code index (a call graph / module map from
   another tool, or notes in `.brse/knowledge/`) — read it first for module
   boundaries. None → skip; don't ask the user to install anything for this.
1. **Locate** with
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py extract-refs <path> <keyword1> <keyword2> ...`
   (business terms, screen names, route names, table names in scope).
   `rg` missing (`{"error": "ripgrep (rg) not installed"}`) → use the Grep
   tool with the same keywords, and say that this path skips the script's
   Shift-JIS (cp932) retry, so a legacy-encoded file may be missed.
   Search results only *locate* code — they never support a conclusion.
2. **Find the entry points**: route / controller action, CLI command, batch
   schedule entry, screen event, queue consumer.
3. **Trace end to end and read each function in full** along the path:
   entry → validation → service / domain logic → data access (tables,
   columns, transactions) → external effects (mail, API, file, queue, cache).
   Don't read every file a keyword hit — read what the flow actually calls.
4. Scope larger than ~10 files → module by module into an intermediate draft,
   then consolidate. Parallel subagents per module are fine (spec section
   11); each reads `.brse/memory/long/glossary.md` first and never writes to
   `.brse/memory/`.
5. A hit whose relevance is uncertain → list it under *Found, relevance
   unconfirmed*; don't drop it and don't fold it into the conclusion.
6. Before trusting an existing DD/spec for this flow → check
   `.brse/memory/long/decisions-log.md`; the DD may lag behind a QA decision.

## Output

1. **Overview** — what the flow does, in business terms, 2–3 lines.
2. **Entry points** — each with `file:line`.
3. **Flow** — numbered steps, each with `file:line`.
4. **Conditions and validation** — table: condition | result | `file:line`.
5. **Data written / read** — table, column, when.
6. **External effects** — mail, API, files, queues.
7. **Unknowns** — what the code doesn't settle (config values, data-driven
   branches) and who could answer.

Every sentence cites `file:line`, inline or inside `config.style.source_tag`.

## Checks before answering

- Every step of the flow was read in the code, not inferred from a name.
- Every sentence has a `file:line`.
- Run `verify-output`.

## Handoff

Finish with `review-gate` — it runs `verify-output` as its last step.
