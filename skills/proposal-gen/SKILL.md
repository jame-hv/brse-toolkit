---
name: proposal-gen
description: Use this when the user has requirements (spec, client emails, meeting notes) that need to be turned into a proposal. Produces two separately authored drafts — internal technical version and client-facing version — not one draft mechanically trimmed down.
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

Requirements (RFP, spec, client emails, meeting notes) need to become a
proposal (提案書) — usually a slide deck in the client's or the company's
template.

## Steps

1. **Restate**: reader (client / internal), format (a deck when a `.pptx`
   template exists in `config.paths.templates`), deadline, and the sections
   the client asked for. An RFP that lists required sections or evaluation
   points → those sections, in that order and numbering, are the skeleton.
2. **Read every source in full** — RFP body and every attachment, all slides
   and sheets, images and diagrams included. Build a requirements list
   `R-01, R-02, …`, each with its source ref. Read the estimate, if one
   exists: scope, effort, schedule and price in the proposal come from it.
3. **Outline before writing**: section → slide titles → which `R-` ids each
   answers. Deck longer than ~5 slides → show the outline and get a yes first.
4. **Write each slide**:
   - The title states the message ("Cutover is done by the client, we
     provide the runbook"), not a topic ("Cutover").
   - At most 5 bullets, short phrases, one idea each. No paragraphs.
   - Numbers (effort, schedule, price, counts) equal the estimate — cite the
     sheet and cell in the speaker notes.
   - Every abbreviation, internal ID or code is explained at first use, or
     left out of the client version.
   - Not decided yet → goes to a 前提条件 / 確認事項 slide, never stated as
     fact.
5. **Diagrams, not text** for current architecture, new architecture and
   process flow: use the diagram tool `/brse-toolkit:doctor` reports
   (draw.io first); start from any existing diagram in the sources and keep
   its notation.
6. **Two versions only when asked**: internal (technical detail, risks,
   assumptions, effort breakdown) and client-facing (scope, approach,
   benefits, assumptions, what the client must do). Write each for its
   reader — never produce one by trimming the other.
7. **Produce the file via `report-gen`** into a copy of the template, then
   render every slide to an image and look at it: no text overflow, fonts and
   colours as in the template, no element cut off, diagrams readable.

## Output

The file path, then:

| Slide | Message (title) | Answers |
|---|---|---|

**RFP coverage:** each required section / evaluation point → slide, or
"not answered" with the reason. **Open questions for the client:** …

## Checks before answering

- Every `R-` id is answered or explicitly marked out of scope.
- Every number matches the estimate (cell refs in the notes).
- Every slide image was looked at after rendering.
- The user's corrections in this task are all applied (feedback ledger).
- Run `verify-output` on both versions.
