---
name: testcase-review-jp
description: Use this when the user needs a test case list (単体テスト仕様書 / テストケース) reviewed against its corresponding Detail Design document (詳細設計書) before test execution or client sign-off — checking the design first, then verifying each test case row is logically consistent with it, flagging mismatches or unsupported cases, and producing a findings report.
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

User has a test case list and its matching Detail Design document (same
screen/feature) and wants to know whether the test cases are logically sound
before testing starts or before the list goes to the client — not a request to
just translate or reformat the test case list.

**Not this skill**: comparing two versions of the *same* document type (old
spec vs new spec, old test case vs new test case) — that's `cross-check`'s
structural diff. This skill compares two *different* document types (design
vs test case) on meaning, not structure — every row needs judgment, not a
mechanical key/value diff.

## Step 1 — Analyze the design

Read the Detail Design file with `excel-analyze`
(`${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py`),
covering every sheet in scope (Japanese SI detail designs typically split into
screen/field spec, event/button logic, server logic, return-value tables, and
a screen-image sheet — read all of them, not just one).

Turn the design into a list of identifiable rules, each tagged with its
source location (sheet + cell/section): field specs (required/optional, type,
length, default value), validation rules, business logic/processing flow,
show/hide conditions, error messages. Something the design doesn't state →
record as "not covered by design", never inferred or guessed.

## Step 2 — Check every test case row against the design

Read the test case sheet with the same `extract-cells.py`. Column names vary
by client template (常見: precondition / steps / expected result, or
No./category/precondition/procedure/expected result) — read the header row
first to map columns before checking rows.

For **every** row, find the matching design rule(s) from Step 1 (match by
field name, screen area, or business flow name) and compare, then mark one of:

- ✅ **Consistent** — row reflects the design correctly.
- ⚠️ **No basis found** — design doesn't cover this case; flag it to ask the
  client/BA, don't guess whether it's right or wrong.
- ❌ **Inconsistent** — clear conflict with the design (wrong condition, wrong
  value/boundary, expected result contradicts the design's logic, a
  design-required case is missing, or an extra case not grounded in the
  design).
- 🔁 **Needs confirmation** — suspicious but the design's wording is itself
  ambiguous.

No row skipped, including rows that look trivial (page title, header/footer
checks) — inconsistencies hide in "obvious" rows too.

**Batch processing**: test case list has more than ~30 rows → dispatch in
parallel by category/section (spec section 11), one subagent per
category/section. Each subagent gets only the design rules relevant to its
slice + its rows — never the whole design and whole test case list. Main
agent aggregates the per-row markers; a conflict between two subagents' calls
on overlapping design rules → ask the user, don't resolve it silently.

## Step 3 — Consolidate the review report

Report only the ⚠️/❌/🔁 rows (✅ rows get a count, not a full listing). Each
reported row includes: test case No. + item name, a short quote of what's
being questioned, why it's inconsistent, the design reference it conflicts
with (or the absence of one), and a suggested fix when there is an obvious one.

Output is a **separate** review report (chat/markdown, or a new file) — never
edit or overwrite the client's original test case file. If the user wants the
findings marked directly inside the Excel (comment or cell highlight),
confirm first and always write to a copy, never the original.

Test case and design both carry EN/JP columns and a row is only inconsistent
in one language → check `.brse/memory/long/glossary.md` / use `jp-vi-translate` before
concluding it's a translation slip rather than a logic slip.

## Before answering

Apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on
the draft response before sending. Every reported row needs a source tag for
**both** sides being compared, in `config.style.source_tag` or inline as
`Sheet!A12`: the test case cell and the design cell (or an explicit
"not covered by design" note, in the reply language, when there is none).
