---
name: proposal-gen
description: Use this when the user has requirements (spec, client emails, meeting notes) that need to be turned into a proposal. Produces two separately authored drafts — internal technical version and client-facing version — not one draft mechanically trimmed down.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"
- Running as a subagent dispatched by a main agent (spec section 11 batch processing) → the main agent has already resolved this gate before dispatching — do not re-trigger the stop-and-ask, proceed directly. Only apply the check above when invoked directly with no parent agent to have already cleared it.

## Trigger

There are requirements (spec, client emails, meeting notes) that need to be
synthesized into a proposal.

## Mechanism (spec section 6.8)

1. Extract requirements from the sources (`documents/`, `memory/decisions-log.md`)
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
