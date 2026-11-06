---
name: cross-check
description: Use this when the user wants two sources compared against each other (old vs new spec, code vs spec, Excel vs Excel), wants to know if `.brse/memory/long/` entries went stale after a source document changed, or wants decisions-log.md reconciled against an updated DD.
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

## Getting the old version of a document from git history (spec section 3)

`/brse-toolkit:init` runs `git init` specifically to support this step — the old
version of a document does NOT live in a same-named file like
`spec_v2.xlsx`/`spec_v3.xlsx`, it lives in the project directory's git history.
Before diffing:

1. Check the file's commit history: `git -C <project-dir> log --oneline -- <source-folder>/<relative-path>`  (`<source-folder>` = one of `config.paths.sources`).
2. Extract the old version to a temp file to diff against the current one:

       git -C <project-dir> show <rev>:<source-folder>/<relative-path> > <scratch-dir>/<name>-old.<ext>

   (`<rev>` = the commit hash/tag of the version the client sent previously; for
   binary files like `.xlsx`, remember to redirect to a file, don't read straight
   to stdout.)
3. Parse both the old version (temp file) and the new version with the matching
   adapter below, then diff.

The project directory isn't a git repo yet, or the file was never committed →
there is **no** old version to compare against. State this limitation plainly
in the output, don't guess what the old version looked like.

## 3 kinds of source pairs (spec section 6.2)

- **Old spec vs new spec**: parse both into `[{"key": "<field/page>", "value": "<content>"}]`,
  run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/cross-check/scripts/diff-structured.py old.json new.json`.
- **Code vs spec**: get the actual logic from `code-to-business`, cross-check it
  against the spec description using the same mechanism above.
- **Excel vs Excel**: run `${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py`
  on both files, convert to `{key, value}` using the table's key column, then
  diff. There is no script for this conversion step — `extract-cells.py`
  only ever emits one record per cell (`{"cell": "A2", "value": ...}`), never
  grouped rows, so the key-column choice and header-row handling are a
  judgment call made explicitly each time, not inferred: read the sheet's own
  header row first to identify which column is the item/field name (the key)
  and which column holds the value being compared, skip the header row(s)
  themselves as data, and state the two column letters chosen in the output
  so the comparison is reproducible. A row whose key column repeats (same
  item name twice in one sheet) → `diff-structured.py` silently keeps only
  the last occurrence per key — flag duplicate keys in the source sheet
  before diffing rather than letting them silently disappear.

**Real limitation**: only the parts that can be converted to `{key, value}` can
be compared. Free-form prose can't be structurally compared — fall back to
sentence-by-sentence comparison, lower confidence, and state clearly in the
output which mode is being used.

## Batch processing (multiple independent units)

Multiple independent source pairs need cross-checking in the same request (e.g.
5 spec files all have a new version) → dispatch in parallel (spec section 11),
one subagent per pair. Each subagent reads the relevant `.brse/memory/` entries itself
before comparing. The main agent aggregates results, dedupes overlapping
"needs re-verify" entries, then asks the user once. **Subagents never write to
`.brse/memory/` themselves.**

## Detecting stale `.brse/memory/` entries

Every entry in `.brse/memory/long/*.md` has a source + version/date (spec section 3). When
a diff finds a field that changed between the old/new version, search
`.brse/memory/long/*.md` for any entry that cites that same field in the old version →
flag it "needs re-verify" right in the response, don't confidently keep using
the old value.

## Reconciling `decisions-log.md` against the DD

When the DD/spec is updated: for every entry in `.brse/memory/long/decisions-log.md` whose
`Status in the official doc` is not `FULLY updated` and whose `Status` is
`active` (field names as scaffolded by `/brse-toolkit:init`), check whether the
new DD now reflects that
decision — if it does, ask the user to confirm updating the entry's status; if
not, keep flagging it.

## Before answering

Apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on the
draft response before sending.
