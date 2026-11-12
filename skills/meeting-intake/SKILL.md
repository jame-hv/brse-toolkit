---
name: meeting-intake
description: Use this after any meeting, call or client message that may change the project — minutes (議事録), rough notes, a transcript, a pasted chat, or just the user's one-line summary — to record the meeting, extract decisions, answers to open Q&A, new questions and tasks into the project registers, and hand the changes to change-impact.
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

Something was said that may change the project: a meeting, a call, a client
email/chat, an answered Q&A sheet, or the user saying "chốt là …". Works with
**whatever input exists** — never stop because there are no formal minutes:

| Input | How to read it |
|---|---|
| 議事録 / minutes file (any format) | `brse.py kb-ingest`, then read the converted part |
| Rough notes, pasted chat, email | read as given |
| Audio / video | transcribe if a tool exists (`whisper` on PATH); otherwise say so in one line and work from whatever text the user gives |
| Answered Q&A sheet from the client | ingest; map each answer to its `Q-xxx` by number or wording |
| One-line summary from the user ("khách chốt dùng lại module cũ") | treat as a decision with source "user, <date>" |

## Steps

`brse.py register` below = `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py register`.


1. **Load context** (no questions yet): `brse.py register status`, `brse.py register list --open`,
   and `.brse/memory/long/`. Everything already recorded is never asked again.
2. **Record the meeting**: `brse.py register add M --title "<topic>" --set attendees="…"
   --set file="<path of the raw input>"`. Raw input is kept, never edited.
3. **Extract**, each with the exact sentence it came from:
   - **Decisions** → `add D --source M-… --links <R/Q ids>`; if it replaces an
     earlier decision, `--supersedes D-xxx` (search active D first — a
     contradiction with an active D is always a supersede, never two actives).
   - **Answers** to open Q → `update Q-xxx --status answered --set answer="…"`,
     plus the decision it implies.
   - **New questions / unclear points** → `add Q --status draft --links …`.
   - **Tasks** → `add T --owner <anh|client|BrSE|SE|QA|Comtor> --due …`.
   - **Requirements** added / dropped → `add R` or `update R-xxx --status out`.
   Uncertain whether something was decided → record it as `D` with
   `--status proposed`; the user confirms at the gate, not by an extra question.
4. **Sync** each new active decision as one line in
   `.brse/memory/long/decisions-log.md` (other skills read it).
5. **Link back**: `update M-… --add-links <all new ids>`.
6. **Hand off** every new or superseding decision to `change-impact`. If
   nothing changed the scope or approach (only tasks / notes), skip it.
7. **Minutes for the client** only if the user asks: the draft goes to Comtor
   for wording; never send.

## Output (short, conclusion first)

```
M-2026-11-09 recorded: 2 decisions (1 replaces D-006), 3 answers, 2 new Q, 4 tasks.
Needs your yes: D-015 (proposed) — <one line>.
→ change-impact running on D-014.
```
