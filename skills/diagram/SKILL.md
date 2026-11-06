---
name: diagram
description: Use this when the user needs a system architecture, AWS/cloud, network, ERP/business process, flow, swimlane, timeline or screen-transition diagram that a client can read — built from a draw.io template, filled from the sources, checked by lint and by looking at the rendered image.
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

Any diagram for a document, slide or review: architecture (AWS / Azure / GCP /
on-premise), network, business process (BPMN, swimlane), ERP module or data
flow, timeline / phases, UML, screen transitions.

## Never draw from scratch

draw.io ships ~150 professional templates (AWS, Azure, GCP, IBM, network,
BPMN, swimlane, timeline, archimate, UML, flowchart, wireframes…). Always start
from the closest one, or from an existing diagram in the project's sources.

## Steps

1. **Restate**: what the diagram must show, the reader, label language, where
   it goes (slide → landscape, ≤ ~15 elements; document → can be denser).
2. **Content from sources.** List every element and connection with its
   source (`kb-search.py`, code inventory, decisions-log). Assumed elements are
   labelled "要確認 / to confirm". Nothing is added for decoration.
3. **Pick the base**:
   - an existing project diagram (`.drawio` in the sources, or an image read
     with `image-analyze`) → keep its structure and notation;
   - otherwise `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/drawio-tool.py templates <filter>`
     (e.g. `aws`, `network`, `swimlane`, `bpmn`, `timeline`) → copy one with
     `drawio-tool.py template <name> <out.drawio>` into `config.paths.outputs`
     and render it once to see it.
4. **Adapt by id**: `drawio-tool.py cells <file>` lists every element; write a
   changes JSON (`set` labels, `delete` what doesn't exist in this system —
   a group's contents go with it — `add` by cloning an element of the same
   kind so styles and icons stay consistent, `connect` new flows) and run
   `drawio-tool.py edit`. Iterate in small steps.
5. **Lint**: `drawio-tool.py lint <file>` — no orphans, no dangling or loose
   edges, no overlaps; duplicate labels only where intended.
6. **Render and look**: `drawio-tool.py export <file> <out.png>` (handles
   draw.io's snap sandbox). Open the PNG: every label readable and in the
   right language, arrows point the right way, nothing cut off, the picture
   answers step 1. Fix and repeat until it does.
7. No draw.io available → Mermaid text, clearly marked as not rendered.

## Output

`.drawio` + `.png` paths, a table element → source, what is marked "to
confirm", the lint result. Then `review-gate`.
