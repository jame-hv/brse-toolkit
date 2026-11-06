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
   `drawio-tool.py edit`. An icon that only exists in another template or
   diagram: `add` with `"from": "template:<name>"` or `"from": "<file.drawio>"`.
   Iterate in small steps. Never stop to ask the user how the plugin's tools
   work — if a tool truly cannot do something, say what is missing in one line
   and draw the closest correct version.
5. **Lint**: `drawio-tool.py lint <file>` — no orphans, no dangling or loose
   edges, no overlaps; duplicate labels only where intended.
6. **Render and look**: `drawio-tool.py export <file> <out.png>` (handles
   draw.io's snap sandbox). Open the PNG: every label readable and in the
   right language, arrows point the right way, nothing cut off, the picture
   answers step 1. Fix and repeat until it does.
7. **No template fits**: write a model JSON and run
   `drawio-tool.py build <model.json> <out.drawio>`. Positions are never typed:
   `"layout": "swimlane"` (lane = who does it, `col` = order of the step — for
   business flows) or `"layout": "auto"` (layered from the arrows — for system
   overviews). Every node and edge carries `"ref": {"file", "part", "quote"}`
   from the documents; without one it is drawn dashed as unconfirmed. The
   build writes `<out>.sources.md` (show it next to the diagram) and
   `<out>.claims.json` (run `verify-claims.py` on it). Kinds — groups
   (`aws-cloud`, `region`, `vpc`, `public-subnet`, `private-subnet`,
   `datacenter`, `account`), nodes by kind (`drawio-tool.py kinds`: alb, ec2,
   rds, s3, sqs, lambda, ecs, cloudfront, waf, pc, mobile, users, server…,
   plus `box`, `todo` for unconfirmed parts, `note`, `title`), edges with
   `label`, `dashed` for unconfirmed links and `points` to route around
   boxes. Then steps 5–6. **Never write draw.io XML by hand or with an ad-hoc
   script.**
8. No draw.io available → Mermaid text, clearly marked as not rendered.

## Acceptance — a diagram is shown to the user only when all 8 pass

| # | Criterion | Checked by |
|---|---|---|
| 1 | Purpose: the title says what question it answers; the model states `question` and `reader` | `check` |
| 2 | One view per diagram: a system view (who connects to whom, what flows) **or** a business flow (who does what, in order) — never both | `check` |
| 3 | Correct: every box and arrow has a source whose quote really is in that document; unsourced ones are dashed | `check` (opens the documents) |
| 4 | Complete: every system, person and step in the source section is on the diagram, or listed as left out with the reason | reviewer agent with the sources table and the documents |
| 5 | Meaningful positions: computed (lanes = who, columns = order; or layered from the arrows) or taken from a template | `check` |
| 6 | Readable: ≤ 15 elements, labels ≤ 2 short lines, one language, no abbreviations, every link between systems says what flows, no overlaps, no arrow through a box | `check` + look at the image |
| 7 | Changes marked match the change table of the analysis, one by one | `check --changes <table.json>` |
| 8 | Reader test: a fresh reviewer that sees **only the image** says who does what, in which order, and what changes — and gets it right | `reader-test` |

Commands:
- `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/drawio-tool.py check <file.drawio> --changes <changes.json>`
  (changes.json = `[{"id": "<element id>", "status": "changed|new|removed"}]`,
  the same items as the analysis' change table). Exit 1 = a criterion failed;
  fix the model, rebuild, check again.
- Criterion 8: `drawio-tool.py reader-test <file.drawio>` writes the question
  prompt; export the PNG; give **only the PNG and that prompt** to the plugin's
  `reviewer` agent (or a second model) with no other context; save its JSON
  answer; `drawio-tool.py reader-test <file.drawio> --score <answers.json>`.
  Every `missed` / `wrongly_seen` item is a place the picture does not say
  what it should — fix the diagram, not the answer.
- Criterion 4: give the reviewer the `.sources.md` table and the source
  section; it lists anything in the source missing from the diagram.

## Output

`.png` + `.drawio` paths, the sources table, and one line per criterion
(pass / fail and why). A failed criterion is fixed before showing, or stated
first if it cannot be fixed. Then `review-gate`.
