---
name: research-jp-tech
description: Use this when the user needs to research a technology, regulation, or best practice, prioritizing Japanese-language and authoritative sources over generic English results.
---

## Before running

Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/brse-config.py` and read its JSON:
- `error` → show it to the user and stop; the config file must be fixed first.
- `workspace_root` is null → the folder isn't initialized. Ask once: run
  `/brse-toolkit:init` first (recommended — memory and knowledge get saved for
  next time) or continue once without saving. Running as a subagent dispatched
  by a main agent → the parent already resolved this; proceed.
- Otherwise use `config.paths` (`sources`, `templates`, `outputs` — relative to
  `workspace_root`), `config.style`, `config.translation`, and the files in
  `.brse/memory/long/`. Never assume a folder name the config doesn't list.
- `warnings` not empty → mention them in one line (likely a typo in the config).

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
  whether to save it to `.brse/memory/long/decisions-log.md`, to avoid re-researching the
  same question later.

## Output

A synthesis with sources attached (URL + date); anything without a source
doesn't go into the conclusion.
