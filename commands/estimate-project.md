---
name: estimate-project
description: Run the whole estimation workflow for a set of client documents — intake, scope analysis, Q&A to the client, answers back into decisions, the estimate, and a final consistency check — stopping at each gate for the user's approval and remembering which stage the project is at
---

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs.

Read `.brse/memory/long/estimate-status.md` first (create it if missing):
it records the stage, the files of each stage and open items. Continue from
the recorded stage; never restart silently. Update it at the end of every stage.

| Stage | What happens | Skill / tool | Gate (stop, show, wait for yes) |
|---|---|---|---|
| 1 Intake | ingest every document; manifest of read / partial / unreadable; read partial items visually | `/brse-toolkit:ingest`, `excel-analyze`, `image-analyze` | — |
| 2 Scope | requirement list R-xxx, gap list G-xxx | `scope-analysis` | user confirms both lists |
| 3 Q&A | Q&A sheet in the client's template and language, priority A first | `scope-analysis`, `qa-tone-brse` | user approves before sending; the sent file goes to `config.paths.deliverables` and `.brse/memory/long/deliverables-log.md` |
| 4 Answers | client's answered Q&A is ingested; each answer → decisions-log + R-list update; unanswered → explicit 前提条件; new questions → back to stage 3 | `qa-tone-brse`, `cross-check` | user confirms the decisions |
| 5 Estimate | work items mapped to R-ids, every number with its basis, 前提条件 / not-included from stage 4 with Q&A numbers | `estimation` | user reviews the draft |
| 6 Check | every R-id is in the estimate or in not-included; numbers equal across estimate, Q&A and proposal; review-gate | `cross-check`, `review-gate` | — |

At every stop, say in one line where the project stands and what is needed
from the user or the client next.
