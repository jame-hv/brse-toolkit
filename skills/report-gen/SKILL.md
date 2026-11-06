---
name: report-gen
description: Use this when the user needs to export a report as Excel, Slide, or Word matching the client's template.
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

A report, slide deck or Word document has to be produced in the client's (or
the company's) format.

## Steps

1. **Restate**: reader (client / internal — unclear → ask), format, template,
   where the content comes from.
2. **Content is never invented** (spec section 6.9): status report →
   `.brse/memory/long/decisions-log.md` + `cross-check` / `code-to-business`
   results; proposed solutions → `proposal-gen` first; content the user gave
   → use it as given.
3. **Template**: a client template in `config.paths.templates` → copy it and
   fill the copy; never rebuild its layout from scratch. None → a plain
   default layout, and say in `config.project.reply_language` that the
   default was used and the format needs confirming. (The DD framework under
   `${CLAUDE_PLUGIN_ROOT}/skills/detail-design-jp/templates/` is a different
   thing — spec section 7.)
4. **Pick the format by the content's shape** — not interchangeable:
   - Slide: one message per slide; an unsourced figure goes in the speaker
     notes as "needs confirmation", never on the slide as fact.
   - Excel: row-shaped content (trackers, one row per item); an unsourced
     figure goes in a remark column, not into the tracked value cell.
   - Word: prose; unsourced claims go in a clearly separated internal-notes
     section at the end.
   Ambiguous (e.g. "weekly status report") → ask.
5. **Write the file with the right tool**: the office CLI listed first in
   `config.tools.office_order` for that file type when `/brse-toolkit:doctor`
   found it; otherwise python-pptx / python-docx / openpyxl **opening the
   copied template** (load the existing file — creating a new workbook or
   writing through a DataFrame drops styles, merged cells, images and
   shapes).
6. **Check the result**:
   - Re-read the written file with the same tool and confirm each value
     landed in the intended cell / placeholder.
   - Render pages/slides/sheets to images (office CLI `render`, or
     `skills/excel-analyze/scripts/render-sheet.py`) and look at them:
     overflow, fonts, colours, merged cells, images and shapes still present.
   - Copy of an existing file → list exactly which cells/slides changed;
     nothing else may differ.

## Output

The file path(s), what changed, the checks run, and a separate list of
assumptions / unconfirmed points for the user to review before sending —
kept out of the file itself (in addition to the in-file placement in step 4).

## Checks before answering

- Template formatting preserved (verified on the rendered image).
- No original file overwritten.
- Run `verify-output`.

## Handoff

Finish with `review-gate` — it runs `verify-output` as its last step.
