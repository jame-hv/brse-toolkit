---
name: excel-analyze
description: Use this when the user needs an Excel file read or checked — cell values/formatting, embedded images, or shapes/annotations that need visual rendering to interpret.
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

An Excel file must be read or checked: cell values and formulas, formatting
that carries meaning (colours, strikethrough, comments), pasted images, or
shapes / text boxes / arrows that only make sense visually.

## Steps (spec section 6.3)

0. **Inventory**: every sheet (hidden ones included), its used range, and
   whether it has images, shapes or charts. When `/brse-toolkit:doctor` found
   the office CLI listed first in `config.tools.office_order.xlsx` (e.g.
   `gridcraft-cli info <file> --json`), use it for this inventory and for
   reading ranges (`cat --range`); otherwise use the scripts below. Report the
   inventory — the user must see which sheets were read.
1. **Cells**: `<py> ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py <file.xlsx>` —
   value + font colour + strike + fill colour + comment, read from the XML,
   NOT by vision. Formula cells: the script reports the formula and the
   cached value; a formula with no cached value (file never recalculated) is
   flagged — say so, don't report it as empty.
2. **Meaning of formatting** (what red means, what strikethrough means) —
   NEVER guessed. First time a pattern appears → ask → write it to
   `.brse/memory/long/conventions.md`; from then on apply it without asking.
   A format never confirmed → flag it separately, don't stretch an existing
   convention over it.
3. **Images**: `<py> ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-images.py <file.xlsx> <out_dir>` —
   bytes + anchor cell range (a range, NOT one precise cell — say so when
   citing).
4. **Shapes, text boxes, arrows** that the image extractor can't read →
   `<py> ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/render-sheet.py <file.xlsx> <out_dir>`
   (headless LibreOffice → PNG, prints `{"file": "<path.png>"}`), or the office
   CLI's render/convert when available → pass that PNG to `image-analyze`.
5. **Merged cells**: the value lives only in the top-left cell; the rest read
   empty — never conclude a merged header is blank.

## Output

Per sheet: what it contains, the key values (with `Sheet!A1` refs), meaningful
formatting, images/shapes and what they show. Cell text is exact; anything
read from an image is labelled "read from an image — not 100% certain". Close
with the inventory: sheets read / not read.

## Batch processing

Several independent files or sheets → one subagent per file (spec section 11),
each reading `conventions.md` + `glossary.md` itself. The main agent merges,
dedupes newly found conventions, asks the user once. **Subagents never write
to `.brse/memory/` themselves.**

`extract-cells.py` is also what `qa-tone-brse` uses to read a Q&A list — there
is no second copy.

## Checks before answering

- Every sheet is in the inventory as read or not read (with reason).
- No formatting meaning applied without a confirmed convention.
- Run `verify-output`.

## Handoff

Finish with `review-gate` — it runs `verify-output` as its last step.
