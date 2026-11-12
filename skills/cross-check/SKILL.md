---
name: cross-check
description: Use this when the user wants two sources compared against each other (old vs new spec, code vs spec, Excel vs Excel), wants to know if `.brse/memory/long/` entries went stale after a source document changed, or wants decisions-log.md reconciled against an updated DD.
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

Two sources must agree and the user wants to know where they don't: an
estimate or sheet vs the client's documents, old spec vs new spec, code vs
spec, Excel vs Excel. Also: are `.brse/memory/long/` entries stale after a
source changed, and does `decisions-log.md` match an updated DD.

## Step 0 — Coverage first

1. **Restate**: side A, side B, what "agree" means here (same items? same
   numbers? same wording?), and which sheets / sections are in scope.
2. **List every file on both sides**, and inside each file every sheet,
   slide or page (hidden sheets included). Every one is either read in full
   or listed as *not read* with the reason. Slides and documents are read as
   text, not searched for numbers; images and shapes go through
   `excel-analyze` / `image-analyze`.
   When the workspace has a knowledge index, run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py kb-ingest` first and use
   `.brse/knowledge/manifest.json` as the file list (its `partial` /
   `unreadable` entries are exactly what still needs visual reading or is
   missing); `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py kb-search "<term>"` locates
   candidates across all documents.
3. Keyword search only *locates* candidates — a match/mismatch verdict always
   comes from reading both sides.

## Getting the old version of a document from git history (spec section 3)

`/brse-toolkit:init` runs `git init` for this — the old version of a document
does NOT live in a same-named file like `spec_v2.xlsx`/`spec_v3.xlsx`, it
lives in the project directory's git history. Before diffing:

1. `git -C <project-dir> log --oneline -- <source-folder>/<relative-path>`
   (`<source-folder>` = one of `config.paths.sources`).
2. Extract the old version to a temp file:

       git -C <project-dir> show <rev>:<source-folder>/<relative-path> > <scratch-dir>/<name>-old.<ext>

   (binary files like `.xlsx`: redirect to a file, never read to stdout.)
3. Parse both versions with the matching adapter below, then diff.

Not a git repo yet, or the file was never committed → there is **no** old
version. Say so plainly; don't guess what it looked like.

## 3 kinds of source pairs (spec section 6.2)

- **Old spec vs new spec**: parse both into `[{"key": "<field/page>", "value": "<content>"}]`,
  run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py diff-structured old.json new.json`.
- **Code vs spec**: get the actual logic from `code-to-business`, then compare
  it against the spec's description the same way.
- **Excel vs Excel**: run `${CLAUDE_PLUGIN_ROOT}/scripts/brse.py extract-cells`
  on both files and convert to `{key, value}` using the table's key column.
  `brse.py extract-cells` emits one record per cell, never grouped rows, so the
  key column and header rows are chosen explicitly each time: read the header
  row, pick the item/field column (key) and the compared column (value), skip
  the header rows as data, and state both column letters in the output so the
  comparison is reproducible. A key that repeats in one sheet →
  `brse.py diff-structured` keeps only the last occurrence — flag duplicates
  before diffing.

**Real limitation**: only content that converts to `{key, value}` is compared
structurally. Free prose → sentence-by-sentence comparison, lower confidence;
say which mode was used.

## Counting and totals

Before saying lists or totals match: count the items on each side
independently (A's list, B's list), recompute any total from its parts on
both sides, and compare the counts. A document whose own text and own table
disagree (e.g. "25 modules" above a table of 26) is a finding in itself.

## Batch processing

Several independent pairs → one subagent per pair (spec section 11), each
reading the relevant `.brse/memory/` entries itself. The main agent merges,
dedupes "needs re-verify" entries, asks the user once. **Subagents never
write to `.brse/memory/` themselves.**

## Stale `.brse/memory/` entries

Every entry in `.brse/memory/long/*.md` carries a source and date (spec
section 3). A field that changed between versions → search
`.brse/memory/long/*.md` for entries citing that field in the old version →
flag them "needs re-verify" in the response; don't keep using the old value.

## Reconciling `decisions-log.md` against the DD

When the DD/spec is updated: for every entry in
`.brse/memory/long/decisions-log.md` whose `Status in the official doc` is
not `FULLY updated` and whose `Status` is `active` (field names as scaffolded
by `/brse-toolkit:init`), check whether the new DD now reflects the decision —
yes → ask the user to confirm updating the entry's status; no → keep flagging.

## Output

**Verdict:** e.g. "42 items compared — 40 match, 2 differ, 3 not compared".

| # | Item | Side A (ref) | Side B (ref) | Difference | Suggested fix |
|---|---|---|---|---|---|

**Compared:** what, how many, which mode (structural / sentence).
**Not compared:** item or file + reason.
**Sources read / not read:** from step 0.

## Checks before answering

- Every file, sheet, slide, page in scope is in *read* or *not read*.
- Counts and totals recomputed from both sides.
- Never "everything matches" from a sample — the verdict states how many
  items were compared.
- Run `verify-output`.

## Handoff

Finish with `review-gate` — it runs `verify-output` as its last step.
