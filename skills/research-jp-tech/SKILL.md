---
name: research-jp-tech
description: Use this when the user needs to research a technology, regulation, or best practice, prioritizing Japanese-language and authoritative sources over generic English results.
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

A technology, regulation, standard or best practice needs researching, with
Japanese and primary sources preferred over generic English results.

## Steps

1. **Restate** the question, the decision it feeds, and the exact scope:
   product versions, runtime versions, region/industry. Versions not given and
   they matter (compatibility, deprecations) → ask before searching.
2. **Search in this order** (spec section 6.12):
   1. Japanese government / industry bodies (`.go.jp`, associations) for
      regulation and standards.
   2. Official vendor documentation, release notes, changelogs, upgrade
      guides, package metadata — for the exact versions in scope.
   3. Reputable technical blogs (Japanese first).
   4. English / Vietnamese sources as a supplement.
3. **Read the page itself**, not the search snippet. Record URL, access date,
   and the version the page applies to.
4. **Compatibility questions**: check each version's stated requirement
   (minimum/maximum runtime, removed APIs) one by one and put them side by
   side — don't infer from one version's page.
5. **Confirm empirically when it's cheap and safe** (a minimal check run in an
   isolated environment) and say exactly what was run and the result.
   Otherwise label the finding "documented, not tested".
6. Sources disagree → show both; prefer the newer primary source and say why.
7. Several independent sub-questions → search them in parallel (spec section
   11); the main agent compares and verifies before concluding.

## Output

**Answer:** 1–3 lines.

| Finding | Source (URL · accessed · applies to version) | How verified |
|---|---|---|

**Not found / still uncertain:** …
Japanese terms: keep the original term, add the translation in brackets.

A finding that settles a project question → ask whether to record it in
`.brse/memory/long/decisions-log.md`, so it isn't researched again.

## Checks before answering

- Every finding row has a URL and an access date; nothing comes from memory.
- Version scope is explicit on every compatibility claim.
- Run `verify-output`.
