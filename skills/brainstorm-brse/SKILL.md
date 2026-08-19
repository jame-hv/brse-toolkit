---
name: brainstorm-brse
description: Use this when the user needs solution/business options for a specific problem (e.g. "what are our options for X", "how should we handle Y with the client") — proposes 2-3 structured options with trade-offs, not open-ended code brainstorming.
---

## Trigger

Need to propose a solution for a specific business/process problem.

## Mechanism

Provide 2-3 options, each with:
- A short description.
- A clear trade-off (what you gain, what you give up).
- Risk/impact on the Japanese client side, if any (BrSE-specific — technical
  decisions here usually need to be explainable to the client).
- A recommended option, with the reasoning stated explicitly.

Never give more than 3 options — more choices don't speed up the decision.

## Output

A list of options + recommendation. If any option needs more research before it
can be settled → chain to `research-jp-tech`.

Before answering, apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on the
draft response (trade-offs must have a source, don't write speculation as fact).
