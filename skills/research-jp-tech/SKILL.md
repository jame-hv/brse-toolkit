---
name: research-jp-tech
description: Research technology/regulations/best practices, prioritizing Japanese-language and authoritative sources.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"

## Source priority order (spec section 6.12)

1. Japanese government/organization domains (`.go.jp`, industry associations).
2. Vendor documentation (when researching a specific technology).
3. Reputable technical blogs.
4. English/Vietnamese sources as a supplement, last.

## Mechanism

- Every conclusion must carry a URL + access date (apply `verify-output`) —
  don't summarize and then drop the source.
- Multiple independent sources → search in parallel (spec section 11), the main
  agent synthesizes + verifies before answering, don't let each subagent draw
  its own conclusion and just glue them together.
- Findings relevant to a convention/decision in the current project → ask
  whether to save it to `memory/decisions-log.md`, to avoid re-researching the
  same question later.

## Output

A synthesis with sources attached (URL + date); anything without a source
doesn't go into the conclusion.
