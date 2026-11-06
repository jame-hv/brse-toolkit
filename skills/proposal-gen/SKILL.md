---
name: proposal-gen
description: Use this when the user has requirements (spec, client emails, meeting notes) that need to be turned into a proposal. Produces two separately authored drafts — internal technical version and client-facing version — not one draft mechanically trimmed down.
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

There are requirements (spec, client emails, meeting notes) that need to be
synthesized into a proposal.

## Mechanism (spec section 6.8)

1. Extract requirements from the sources (`config.paths.sources`, `.brse/memory/long/decisions-log.md`)
   → group by category (scope, constraints, risks, estimates).
2. Apply the relay model (spec section 2) at the CONTENT-writing step itself,
   not just at presentation:
   - **Internal technical version**: keep full technical detail/terminology,
     used to settle scope with the dev team before sending to the client.
   - **Client-facing version**: simplified, no unexplained internal jargon,
     internal forms of address never translated verbatim. Multiple options →
     chain through `brainstorm-brse` for clear trade-offs.
3. Every item in both versions points back to its original requirement source.
4. Export the file via `report-gen`.

## Output

Internal proposal + client-facing proposal (if the client version was requested).

Before answering, apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on
both drafts (the client-facing version especially must be free of vague
language and fully sourced).
