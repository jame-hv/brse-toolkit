---
name: code-to-business
description: Use this when the user needs business logic explained or documented from existing, undocumented source code for one concrete feature/flow — never "the whole codebase". Every output sentence cites an exact file:line via extract-refs.py.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"
- Running as a subagent dispatched by a main agent (spec section 11 batch processing) → the main agent has already resolved this gate before dispatching — do not re-trigger the stop-and-ask, proceed directly. Only apply the check above when invoked directly with no parent agent to have already cleared it.

## Trigger

Need to understand business logic from source code — never read "the whole
codebase", a concrete scope is required (1 feature/business flow, e.g. "inventory
order flow"). Scope unclear → ask, don't pick one arbitrarily.

## Strategy for large codebases (spec section 6.10)

0. If the project has already run `/inspect` (the `code-inspector`/`brse-cowork`
   plugin) and a knowledge graph JSON exists — read that first to get module
   boundaries and call relationships instead of re-deriving structure from
   scratch. It's a different plugin (Tree-sitter-based, not part of
   brse-toolkit), so skip this step if it wasn't run; don't tell the user to
   run it just for this.
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
   parallel per module (spec section 11) — each subagent reads `memory/glossary.md`
   before analyzing, and NEVER writes to `memory/` itself.
4. Matches found but relevance uncertain → list separately as "found but relevance
   unconfirmed" — don't discard them or fold them into the main conclusion on your own.

## Output

A business logic document (conditions, processing flow, validation), every
description sentence with `(nguồn: file:dòng)` — the literal Vietnamese source
tag `verify-output`'s lint script checks for, not a translatable phrase.

## Before trusting existing DD/spec content

Check `memory/decisions-log.md` first — the DD may not yet reflect the latest
QA decision (spec section 3).
