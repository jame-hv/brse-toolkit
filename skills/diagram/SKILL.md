---
name: diagram
description: Use this when the user needs a system architecture diagram, process/flow chart, screen transition or cutover plan drawn as a real diagram (draw.io, exported to PNG) — based on the existing diagrams in the project, not invented from scratch.
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

A diagram is needed: current / new system architecture, data or process
flow, screen transitions, cutover or migration phases, org/role charts.
Text bullets are not a substitute when the user or the deliverable asks for a
diagram.

## Steps

1. **Restate**: what the diagram must show, who reads it (client /
   internal), the language of labels, where it goes (a slide, a document,
   standalone).
2. **Start from what exists.** Search the sources for existing diagrams
   (`.drawio`, images in slides/sheets/documents —
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/kb-search.py` and the knowledge
   manifest's `partial` entries). An existing diagram of the same thing →
   keep its structure, notation, groupings and naming; redraw it cleaner,
   don't redesign it. Read it with `image-analyze` when it's an image.
3. **Get the content from sources, not imagination.** Every box and arrow
   corresponds to something in the sources or a confirmed decision; anything
   assumed is drawn dashed and labelled "to confirm".
4. **Draw** a native draw.io file (`.drawio`, mxGraph XML) in
   `config.paths.outputs`:
   - one direction of flow (left→right or top→bottom), aligned grid,
     consistent box sizes;
   - containers for boundaries (client side / our side, AWS account, network
     zone) instead of free-floating labels;
   - orthogonal connectors, no diagonal lines crossing boxes, labels on
     arrows only when they add information;
   - no decorative clip-art that hides the structure.
5. **Export and look**: the diagram tool reported by `/brse-toolkit:doctor`:
   `drawio -x -f png --normalize -o <out.png> <file.drawio>` (add
   `--layout verticalFlow` / `horizontalFlow` when positions need tidying).
   Open the PNG and check: nothing overlaps, every label readable, arrows
   point the right way, matches step 1. Fix and re-export until it does.
   Headless Linux where the export fails to start → try `xvfb-run drawio …`,
   and report if it still fails.
6. **No draw.io available** → write a Mermaid file (`.mmd`) instead; draw.io
   can export it later. Say that it was not rendered and looked at.

## Output

The `.drawio` (or `.mmd`) and `.png` paths, what each element is based on
(source refs), and what is drawn as "to confirm". Then `review-gate`.
