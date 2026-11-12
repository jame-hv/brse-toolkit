---
name: doc-to-md
description: Use this when project documents (Word, Excel, PowerPoint, PDF, legacy .doc/.xls, HTML) must be turned into Markdown with deterministic tools — not AI rewriting — and saved in the project so later analysis, test design and review read the same text the client wrote.
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

First step before analysing a spec, designing test cases or reviewing a
document set. Not for translation or summarising — this skill never rewrites a word.

## Rules

- **Tools only, no AI.** Text comes from scripts, never retyped, paraphrased,
  "cleaned up" or translated. If a conversion is wrong, fix the conversion.
- **One place for converted text: `.brse/knowledge/docs/`** (the same place
  `/brse-toolkit:ingest` uses). Never touch the originals.

## Steps

1. **Standard path = ingest.** Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py kb-ingest`
   (follow `commands/ingest.md`). It converts every file under
   `paths.sources` / `internal` / `deliverables`, writes the Markdown copies,
   `manifest.json` and the search index, and skips unchanged files.
2. **Fallback for files ingest marks `unreadable`** (legacy .doc/.xls/.ppt,
   .rtf, .odt, odd PDFs): run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py doc2md <file> --out <workspace_root>/.brse/knowledge/docs/<its source folder>`
   (MarkItDown, LibreOffice round-trip, pdftotext). Say which files used it.
   Outside an initialized workspace (one-off), the same script with
   `--out <source folder>/docs-md/` — and say nothing is indexed.
3. **`partial` files** (shapes, images, charts, flow sheets, screen images):
   read them with `excel-analyze` / `image-analyze`; never present the
   Markdown copy as the complete content.
4. Scanned PDF with no text → say OCR is needed; never invent the text.

## Output

Counts (converted / unchanged / partial / unreadable), the list of partial and
unreadable files inline, and the fallback files.

## Handoff

Next skills read `.brse/knowledge/docs/` and search with `brse.py kb-search`:
`scope-analysis`, `test-design`, `business-explain`, `testcase-review-jp`.
Finish with `verify-output` on the reply.
