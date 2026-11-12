---
name: estimate-project
description: Run the whole estimation workflow for a set of client documents — intake, scope analysis, Q&A to the client, answers back into decisions, the estimate, and a final consistency check — stopping at each gate for the user's approval and remembering which stage the project is at
---

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs.

**The steps are held by code:** `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py run start estimate --file <estimate copy>`
and `brse.py run status` (see the `estimation` skill, step 0). Stop for the
user only at the approval of the requirement list. A correction the user
gives during the work is applied at once and reported — never asked back.

Read `.brse/memory/long/estimate-status.md` first (create it if missing):
it records the stage, the files of each stage and open items. Continue from
the recorded stage; never restart silently. Update it at the end of every stage.

**Registers are the source of truth** (`<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py register`):
every requirement, gap, question, decision, task and meeting gets an ID there
(R / G / Q / D / T / M), and every approach / estimate version is recorded with
`brse.py register bump`. Run `brse.py register status` at the start — what is recorded is
never asked again.

| Stage | What happens | Skill / tool | Gate (stop, show, wait for yes) |
|---|---|---|---|
| 1 Intake | ingest every document; manifest of read / partial / unreadable; read partial items visually | `/brse-toolkit:ingest`, `excel-analyze`, `image-analyze` | — |
| 2 Scope | requirement list R-xxx, gap list G-xxx, each added to the registers | `scope-analysis` | user confirms both lists |
| 3 Q&A | Q&A sheet in the client's template and language, priority A first; one point per question, with a proposed answer the client can just confirm; each question a `Q-xxx` (sent → `brse.py register update Q-xxx --status sent`) | `scope-analysis`, `qa-tone-brse` | user approves before sending; the sent file goes to `config.paths.deliverables` and `.brse/memory/long/deliverables-log.md` |
| 4 Answers | client's answered Q&A is ingested; each answer → `D-xxx` + R update; unanswered → explicit 前提条件; new questions → back to stage 3 | `meeting-intake`, `change-impact` | user confirms the decisions |
| 5 Estimate | work items mapped to R-ids, every number with its basis, 前提条件 / not-included from stage 4 with Q&A numbers; in the project's own template (any layout); `brse.py register bump estimate` | `estimation` | user reviews the draft |
| 6 Check | every R-id is in the estimate or in not-included; numbers equal across estimate, Q&A and proposal; review-gate | `cross-check`, `review-gate` | — |

At every stop, say in one line where the project stands and what is needed
from the user or the client next.

## Changes can arrive at any stage

The stages are not a straight line. A meeting, a client answer, a new
document or the user's decision can arrive at any time, including after the
estimate was sent:

1. `meeting-intake` records it (minutes, notes, a transcript, a pasted chat or
   a one-line summary all work — never wait for formal minutes).
2. `change-impact` traces what it touches and shows **one** change proposal.
3. After the user's yes: registers updated, approach / estimate get a new
   version with a change log, new questions go back to stage 3, and the stage
   in `estimate-status.md` moves back to the earliest stage affected.

New files dropped in the project's `00_inbox/` are handled the same way:
ingest, classify (client document / minutes / answered Q&A), file into the
right folder, then steps 1–3.

