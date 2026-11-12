---
name: change-impact
description: Use this when a decision, Q&A answer or requirement changes — after a meeting, a client answer or the user's instruction — to trace everything it affects (requirements, approach, estimate lines, Q&A, tests, tasks), show one change proposal for the user to approve, then apply it with new approach/estimate versions and a change log.
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

A new or superseding `D-xxx`, an answered `Q-xxx`, or an `R-xxx` added /
dropped — usually handed over by `meeting-intake`. Also on "nếu đổi sang
phương án X thì ảnh hưởng gì?" (run steps 1–3 only, as a what-if; record nothing).

## Steps

1. **Trace**: `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py register impact <id>` for each
   changed item. Then search the current approach and estimate files for those
   IDs (and for the superseded decision's IDs): every estimate row, 前提条件,
   not-included item and approach section that cites them is affected.
2. **Assess each affected thing** — one row each, with the basis:
   - requirement: stays / changes / out of scope
   - approach section: what changes
   - estimate row: old → new effort and why (count × unit, reference, or
     assumption); technical parts from SE, test effort from QA when they move
     by more than a few 人日 (ask them with the IDs and the decision)
   - Q&A: now void / needs rewording / new question needed
   - tests, design, open tasks touched
3. **One change proposal**, conclusion first:
   ```
   D-014 (reuse old module, replaces D-006): estimate −38人日 (412 → 374), approach §3 rewritten,
   Q-011 void, 1 new Q (license of old module), QA test scope −2 screens.
   | # | Item | Now | Proposed | Basis |
   ```
   Each row approvable on its own. Stop and wait for the user's yes / edits.
4. **Apply only the approved rows**:
   - registers: `update` R / Q (void: `--status void`), new Q as draft, new T
     with owners
   - approach file → new version; estimate via the `estimation` skill in the
     project's own template (whatever it is) → new version; both keep a
     change-log sheet/section: date · version · change · reason (D/Q ids)
   - `brse.py register bump approach|estimate --file <path> --reason "…" --decisions D-…`
   - new / reworded Q&A → Comtor for wording in the client's language
5. **Check**: `brse.py register check` and `cross-check` (every in-scope R in the
   estimate or not-included; same numbers in estimate, approach, Q&A).
   `brse.py register render`. Then `review-gate` before anything goes to the client.

## Output

One line: what changed and the new versions (`approach v1.3, estimate v1.4: −38人日`),
then what waits on whom (user / client / which bot). Nothing is sent to the client.
