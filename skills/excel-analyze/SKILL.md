---
name: excel-analyze
description: Use this when the user needs an Excel file read or checked — cell values/formatting, embedded images, or shapes/annotations that need visual rendering to interpret.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"

## Mechanism (spec section 6.3)

1. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py <file.xlsx>` —
   value + font_color + strike + fill_color + comment, read precisely from the XML,
   NOT vision.
2. The meaning of formatting (what red means, what strikethrough means) — NEVER
   guess. First time a pattern is observed → ask for confirmation → write it to
   `memory/conventions.md`. From then on apply it automatically, don't ask again.
   A cell with an unfamiliar, never-confirmed format → flag it separately, don't
   apply an existing convention to it.
3. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-images.py <file.xlsx>
   <out_dir>` — images pasted into the sheet, bytes + anchor cell range (NOT a
   single precise cell — state this limitation clearly when citing it).
4. Shapes/textboxes/arrow annotations that `extract-images.py` can't read →
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/render-sheet.py <file.xlsx> <out_dir>`.
   The script renders to a **PNG** file (headless LibreOffice) and prints JSON
   `{"file": "<path.png>"}` — chain that exact PNG file into the `image-analyze`
   skill (`ocr-pass.py` can only read images, not PDFs).
5. The final report merges both kinds of source, but does NOT present them as
   equally reliable: the cell-text part (fully accurate) and the image/shape
   part (via vision, labeled "read from an image, not 100% certain").

## Batch processing (multiple independent units)

Multiple independent Excel files/sheets need analysis in the same request →
dispatch in parallel (spec section 11), one subagent per file. Each subagent
reads `memory/conventions.md` + `memory/glossary.md` itself before analyzing.
The main agent aggregates results, dedupes newly-found formatting conventions,
then asks the user once. **Subagents never write to `memory/` themselves.**

## Shared with `qa-tone-brse`

`extract-cells.py` is also the script `qa-tone-brse` uses to read back the Q&A
list Excel — there is no second copy of this script anywhere else.

## Before answering

Apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on the
draft response before sending.
