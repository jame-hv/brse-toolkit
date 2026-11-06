---
name: code-to-business
description: Use this when the user needs business logic explained or documented from existing, undocumented source code for one concrete feature/flow — never "the whole codebase". Every output sentence cites an exact file:line via extract-refs.py.
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

## Trigger

Need to understand business logic from source code — never read "the whole
codebase", a concrete scope is required (1 feature/business flow, e.g. "inventory
order flow"). Scope unclear → ask, don't pick one arbitrarily.

## Strategy for large codebases (spec section 6.10)

0. If the project already has a code index (a call graph / module map
   produced by another tool, or notes in `.brse/knowledge/`) — read that first
   to get module boundaries and call relationships instead of re-deriving
   structure from scratch. None exists → skip this step; don't ask the user
   to install anything just for this.
1. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/code-to-business/scripts/extract-refs.py <path>
   <keyword1> <keyword2> ...` with business keywords within the defined scope →
   a list of file:line matches, don't dump whole files into context.
   `rg` not installed (the script exits with `{"error": "ripgrep (rg) not
   installed"}`) → fall back to the `Grep` tool (or `grep -rn`) with the same
   keywords, one call per keyword, over the same scope — but call out in the
   output that this fallback path skips `extract-refs.py`'s Shift-JIS (cp932)
   decode-retry, so a legacy non-UTF-8 file could be silently skipped or
   error out instead of being matched.
2. From the match list, only read (Read tool, just the relevant line ranges) the
   files/functions that are actually part of the flow — don't read every file
   that has a match.
3. Scope spans >~10 files → process file-by-file/module-by-module, write findings
   to an intermediate draft, consolidate in the final step. Can dispatch in
   parallel per module (spec section 11) — each subagent reads `.brse/memory/long/glossary.md`
   before analyzing, and NEVER writes to `.brse/memory/` itself.
4. Matches found but relevance uncertain → list separately as "found but relevance
   unconfirmed" — don't discard them or fold them into the main conclusion on your own.

## Output

A business logic document (conditions, processing flow, validation), every
description sentence citing its `file:line` — either inline (`src/a.py:12`) or
inside the workspace's `config.style.source_tag`, both of which
`verify-output`'s lint script accepts.

## Before trusting existing DD/spec content

Check `.brse/memory/long/decisions-log.md` first — the DD may not yet reflect the latest
QA decision (spec section 3).
