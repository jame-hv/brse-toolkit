---
name: estimation
description: Use this when the user needs an estimate (見積書) created, revised or checked — work items, effort (人日/人月), preconditions (前提条件), scope and not-included items — in the project's estimate template, with every number traceable to its basis.
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

An estimate must be drafted, revised, or checked against the client's
documents / Q&A. (Checking only, with nothing to write → `cross-check`
does the comparison; this skill owns the estimate's structure and content.)

## Steps

1. **Restate**: which estimate (file, sheets), what changes, the input
   sources (RFP, Q&A, source code, previous estimates), what is out of scope.
2. **Template and references.** The project's estimate template from
   `config.paths.templates`, or the estimate file being revised. Also check
   the personal library (`<py> ${CLAUDE_PLUGIN_ROOT}/scripts/library.py list --kind estimate`)
   for an approved estimate of a similar project — reuse its structure and
   wording style; ask before reusing anything from a different client. Never
   change the template's layout, formulas or styles.
3. **Logic chain before numbers.** Write the chain explicitly and show it:
   input (what the client gave) → analysis (what has to change, counted:
   screens, APIs, batches, tables, libraries, environments) → work items →
   effort per item with its basis (count × unit effort, a reference project,
   or a stated assumption). No number without a basis.
4. **Preconditions (前提条件).** One short statement per item, in the client's
   language and register. Only things that bound the estimate (scope,
   responsibilities, environments, inputs the client provides, what triggers
   a re-estimate). Don't copy task lists from other sheets — point to them.
   Don't commit to durations or dates the user hasn't approved.
5. **Scope / Not included.** One item per line, same indentation style as the
   surrounding list. Every "not included" item that came from a Q&A answer
   cites that Q&A number. Nothing appears in both lists.
6. **Work-item rows.** Same granularity as the existing rows (a work item, not
   a sub-step). Short noun phrases in the cell, details in the remark column.
   Bilingual sheet → the translated table sits beside the source table, never
   in alternating columns.
7. **Write** into a copy (`config.paths.outputs`) with the office tool from
   `config.tools.office_order.xlsx`; recalculate formulas (open/save with the
   office CLI or LibreOffice) so totals are current. Highlight only what the
   user asked to highlight.
8. **Verify**: `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/office-diff.py <original> <copy>`
   — only intended cells changed, formatting identical; totals recomputed by
   hand from the rows equal the sheet's totals; every effort figure equals
   the number quoted in the proposal / Q&A, if those exist. Render the sheet
   and look at it.

## Output

The copy's path; a table of changed rows/cells with the basis of each
number; preconditions and not-included items added or changed (with
sources); open questions for the client. Then `review-gate`.
