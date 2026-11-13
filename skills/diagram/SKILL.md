---
name: diagram
description: Use this when the user needs a system architecture, AWS/cloud, network, ERP/business process, flow, swimlane, timeline or screen-transition diagram that a client can read — built from a draw.io template, filled from the sources, checked by lint and by looking at the rendered image. Also the interactive 3D page (Three.js) of a site, warehouse or production line: goods moving between machines, people and terminals placed from the layout drawing, the change spot marked — whenever the user asks to see a site, a flow or a diagram in 3D.
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
   source (`brse.py kb-search`, code inventory, decisions-log). Assumed elements are
   labelled "要確認 / to confirm". Nothing is added for decoration.
2b. **Choose the kind of diagram from the question it must answer** — never a
   default. Write the choice and the question at the top of your reply.

   | Question to answer | Kind of diagram (`needs.type`) |
   |---|---|
   | What the system is made of, what connects to what, what flows between them | system view: boxes + labelled arrows (`system`) |
   | Several people / systems work on one job: who does which step, in which order | flow split by who is responsible (`flow-lanes`) |
   | One person or system goes through steps, with branches | simple flow, no lanes (`flow`) |
   | Phases over time (preparation, cutover, operation) | timeline (`timeline`) |
   | Which screen leads to which | screen transitions (`screens`) |
   | Where servers, network, cloud parts are | infrastructure, from a draw.io template (`infrastructure`) |
   | A site, warehouse or line in 3D: which machines the goods pass, where people and terminals stand, where the change happens | build the diagram, add `"scenes"`, then `brse.py drawio-tool scene3d` (below) |
   | What is inside ONE machine or device, part by part (close-up, not the whole site) | `brse-toolkit:anatomy` |
   | What changes | the SAME diagram as the current state, with changes marked — never a new layout |

   Two questions → two diagrams. A sample from the user or the client
   overrides this table.
3. **Pick the base — only on measured grounds**: a sample from the user or
   the client first. Otherwise write a needs file
   (`{"type": "<kind above>", "kinds": [node kinds the diagram must show],
   "groups": n, "elements": n}`) and run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py drawio-tool suggest <needs.json>`: it reads
   every bundled template's content and ranks them by how many of the needed
   icons each already has. Use the template only when its `decision` says so,
   and state its `basis` (coverage) in the reply; "no template fits" → build
   from scratch (step 7). Never pick a template by its name alone.
   - A sample or an existing project diagram (`.drawio` in the sources, or an
     image read with `image-analyze`) → keep its structure and notation.
   - The template `suggest` chose → copy it with
     `brse.py drawio-tool template <name> <out.drawio>` into `config.paths.outputs`.
4. **Adapt by id**: `brse.py drawio-tool cells <file>` lists every element; write a
   changes JSON (`set` labels, `delete` what doesn't exist in this system —
   a group's contents go with it — `add` by cloning an element of the same
   kind so styles and icons stay consistent, `connect` new flows) and run
   `brse.py drawio-tool edit`. An icon that only exists in another template or
   diagram: `add` with `"from": "template:<name>"` or `"from": "<file.drawio>"`.
   Iterate in small steps. Never stop to ask the user how the plugin's tools
   work — if a tool truly cannot do something, say what is missing in one line
   and draw the closest correct version.
5. **Lint**: `brse.py drawio-tool lint <file>` — no orphans, no dangling or loose
   edges, no overlaps; duplicate labels only where intended.
6. **Render and look**: `brse.py drawio-tool export <file> <out.png>` (handles
   draw.io's snap sandbox). Open the PNG: every label readable and in the
   right language, arrows point the right way, no arrow across a label, nothing
   cut off, the picture answers step 1. Think of it placed on its page: a long
   thin strip shrinks until the text cannot be read — rebuild with
   `"direction": "DOWN"` (or `"RIGHT"`) and keep the one that reads. Fix and
   repeat until it does.
7. **No template fits**: write a model JSON and run
   `brse.py drawio-tool build <model.json> <out.drawio>`. Positions are never typed:
   `"layout": "swimlane"` (lane = who does it, `col` = order of the step — for
   business flows) or `"layout": "auto"` (layered from the arrows — for system
   overviews). Every node and edge carries `"ref": {"file", "part", "quote"}`
   from the documents; without one it is drawn dashed as unconfirmed. The
   **Use draw.io's icons**: every person, device, server, database, external
   system or scheduled job gets `"icon": "<path>"` found with
   `brse.py drawio-tool icons <word>` (about 1,900 files: `active_directory/`
   web_server, generic_server, database_server, user, users, workstation_client;
   `clip_art/computers/`, `clip_art/networking/`, `mscae/`, `azure2/`, `ibm/`,
   `allied_telesis/`, `sap/`). Keep one family where it has the icon. A plain box
   only when nothing fits. The label is placed where arrows do not run.
   build writes `<out>.sources.md` (show it next to the diagram) and
   `<out>.claims.json` (run `brse.py verify-claims` on it). Kinds — groups
   (`aws-cloud`, `region`, `vpc`, `public-subnet`, `private-subnet`,
   `datacenter`, `account`), nodes by kind (`brse.py drawio-tool kinds`: alb, ec2,
   rds, s3, sqs, lambda, ecs, cloudfront, waf, pc, mobile, users, server…,
   plus `box`, `todo` for unconfirmed parts, `note`, `title`), edges with
   `label`, `dashed` for unconfirmed links and `points` to route around
   boxes. Then steps 5–6. **Never write draw.io XML by hand or with an ad-hoc
   script.**
8. No draw.io available → Mermaid text, clearly marked as not rendered.

## Interactive 3D page

`brse.py drawio-tool scene3d <file.drawio> <model.json> <out.html> [--lang ja|vi|en]`
turns a built diagram into one self-contained HTML file (Three.js embedded, opens
offline): orbit, zoom, a flow that plays step by step, the camera following it, and
each step's source quote. Add to the model
`"scenes": [{"title": "...", "edges": ["e0", "e1"]}]` in the order things happen; the
order must come from the documents. `not_in_any_scene` in the result must be empty.
Open it in a browser and look: no console errors, every label readable.

**A real site (factory, warehouse):** find the site's layout drawing first
(配置図, レイアウト図, 平面図; a whole-floor one beats per-line ones). Read where each
machine and area is, and give every node `"at": [x, y]` and every area
`"zones": [{"label", "rect": [x, y, w, h]}]` as fractions of that drawing, plus
`"floor": {"size": [w, d], "ref": {...}}` with the drawing's proportions. Each node's
`"at_ref"` says what on the drawing it was read from. A machine the drawing does not
name gets "(名称要確認)", and control systems that the drawing does not place are
marked as placed for the concept only. Do not lay the drawing itself on the floor:
the user rejected it as hard to read. Keep the floor plain: zones, machines, flow.

**Site model — what to read, in this order, before placing anything.** On the
2026-11-11 trial every one of these changed the model; reading only the overview gave a
model the user rejected as "not reading the request".

1. The request folder, every file, pictures included (slides, mail attachments): what
   changes, where, and what is still open. A picture that is only "<image001.png>" in a
   mail PDF is missing — say so, do not guess its content.
2. The interface specification the request points to (file name, layout, when it is
   sent), and the database definition for the tables and codes it touches.
3. The operation manual and the full system specification for the screens and the flow
   around the change (who presses what, what the machine decides).
4. The label / code specification when numbers or barcodes change; it often has
   whole-floor maps of where labels are printed and read.
5. Any other change request in the same area (a folder named after a date or 改修),
   even an approved one: it can change the same flow.
6. Layout drawings and device lists for positions; manuals' area maps for names.

Write what does not agree between documents into `"brief"` as "to ask before doing",
with both sources.

**Site model — check all of this in one pass before showing it.** Each item comes
from a rejection on a real trial (2026-11-11), where checks done one complaint at a time
let the next fault through.

| # | Check | How |
|---|---|---|
| 1 | The client's request documents were read first; every requested change is on the model, marked `"change"`, and summarised in `"brief"` with its source | read the request folder before the overview |
| 2 | Every machine, person and device from the documents is in a flow, or has `"alone"`: why it stands alone | `scene3d` refuses otherwise (`not_in_any_flow`) |
| 3 | Things the documents name separately stay separate (e.g. SAS and the shuttle) | compare the names in the manuals and the request |
| 4 | Every quote is word for word in its file and page | open each file and search the quote |
| 5 | Every label is in the user's language; the original name is in `"original"` | read the side panel and one detail card |
| 6 | Looked at in the browser: the overview, the first step of each scene, one click on a changed machine, the panel hidden and shown; no console error, no label hiding an area name, no line from another scene | screenshots, each one looked at |

## Acceptance — shown to the user only when these pass

Each check has a stated reason; nothing here is a number picked without basis.

| # | Check | Why | How |
|---|---|---|---|
| 1 | The title says what question the diagram answers and for whom | a diagram drawn "for nobody" was rejected | `check` |
| 2 | One connected story: no island of boxes standing apart (people, devices, systems, documents may all appear together) | the rejected diagram had two unconnected parts | `check` |
| 3 | Every box and arrow has a source, and the quote really is in that document; without one it is dashed "unconfirmed" | "what is your basis for this arrow?" | `check` (opens the documents) |
| 4 | Positions are computed (who / order, or along the arrows) or taken from a template / sample | "what is your basis for these positions?" | `check` |
| 5 | No defects: no overlapping boxes, no arrow attached to nothing | objective faults | `check` |
| 6 | Reader test: a fresh reviewer that sees **only the image** gets who does what, in which order, and what changes right | the reader is the judge of readability | `reader-test` |

Also reported (not blocking, for you and the reader test): element count,
long or mixed-language labels, links between systems without a label, and —
with `--changes` — whether the marked changes equal the analysis' change table.

**Never ask the user how to draw, which kind of diagram, or which template.**
Choose from the question table and `suggest`, draw, check, and show the result
with the reason for the choice. Ask the user only for a fact the documents do
not contain.

Commands:
- `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py drawio-tool check <file.drawio> --changes <changes.json>`
  (changes.json = `[{"id": "<element id>", "status": "changed|new|removed"}]`,
  the same items as the analysis' change table). Exit 1 = a criterion failed;
  fix the model, rebuild, check again.
- Check 6: `brse.py drawio-tool reader-test <file.drawio>` writes the question
  prompt; export the PNG; give **only the PNG and that prompt** to the plugin's
  `reviewer` agent (or a second model) with no other context; save its JSON
  answer; `brse.py drawio-tool reader-test <file.drawio> --score <answers.json>`.
  Every `missed` / `wrongly_seen` item is a place the picture does not say
  what it should — fix the diagram, not the answer.

## Output

`.png` + `.drawio` paths, the sources table, and one line per check
(pass / fail and why). A failed criterion is fixed before showing, or stated
first if it cannot be fixed. Then `review-gate`.
