---
name: memory-review
description: Review recent session logs (.brse/memory/short) and, with the user's approval per item, promote settled terms, conventions, parties, decisions and recurring corrections into .brse/memory/long
---

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs.

1. Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse-config.py`; no workspace → ask
   the user to run `/brse-toolkit:init` and stop.
2. Read `.brse/memory/long/` (all files) and every log in
   `.brse/memory/short/` newer than the `<!-- last-review: YYYY-MM-DD -->`
   marker at the top of `.brse/memory/long/feedback-log.md` (no marker → all
   logs).
3. From the logs, list candidates — only things the **user** said or
   confirmed, never the agent's own guesses:
   - **Terms** (a translation the user chose or corrected) → glossary.
   - **Conventions** (a formatting or writing rule the user stated or
     corrected more than once) → conventions. A sentence or label the user
     rejected is saved as `- wording: "<what was written>" → "<what it should
     say>" — <why> — source, date — status: active`; `wording.py` gives these
     to the reviewer as the standard.
   - **Parties** (who is who, how to address them) → parties.
   - **Decisions** (scope, approach, assumptions the user settled) →
     decisions-log.
   - **Corrections** — every time the user pushed back on the agent's work —
     → feedback-log, each with one category from: `misread-request`,
     `did-not-read-source`, `unsupported-claim`, `out-of-scope`,
     `ignored-feedback`, `format-layout`, `writing-style`, `translation`,
     `wrong-content`, `other`.
   Skip anything already present in `memory/long` (same meaning).
4. Show the candidates as one numbered list grouped by target file, each with
   the session log it came from. Ask the user which to keep (all / numbers /
   none) and let them edit wording.
5. Write only the approved items, in each file's entry schema, with source
   (session log name) and date. A new entry that replaces an old one → mark
   the old one `status: superseded by <date>`, never delete it. Corrections
   go to `feedback-log.md` as
   `- <YYYY-MM-DD> | <category> | <correction, one line> | rule: <the conventions entry it produced, or none>`.
6. Update the `<!-- last-review: ... -->` marker to today.
7. Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/feedback-stats.py --days 30` and
   show the top categories, so the user sees where the agent keeps failing.
