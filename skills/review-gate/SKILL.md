---
name: review-gate
description: Mandatory final check before any work is handed back to the user — restatement vs result, feedback ledger, source coverage, evidence, an independent second-agent review, rendered-file inspection and the lint. Every other brse-toolkit skill ends here; also use it when the user asks "check it again before I look".
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

At the end of every brse-toolkit task, before the reply that hands work back.
Never skipped because the task "looked simple".

## Steps — all of them, in order

1. **Request vs result.** Re-read the user's original message and the
   restatement (`Deliverable / Format / Sources / Out of scope`). Does the
   result deliver exactly that, in that format? Anything missing or extra →
   fix it now, don't hand back.
2. **Feedback ledger.** List every correction the user gave in this task,
   numbered. For each: done / not done, and where it is visible in the
   result. A "not done" item → fix it now or say plainly why it can't be.
3. **Source coverage.** List sources read and not read (with reasons). When
   the workspace has `.brse/knowledge/manifest.json`, compare against it:
   every relevant file there is either read or named as not read; `partial`
   files' images/charts were read visually or named as not read.
4. **Evidence, checked by opening the sources.** Every conclusion has a ref.
   Put the key claims — every number, every quoted requirement or decision,
   every "A differs from B" — into a claims JSON and run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py verify-claims <claims.json>`. Every
   claim must come back `ok`; a `mismatch` / `not_found` is a wrong statement
   — fix the work, not the claim file. Numbers that appear in several
   deliverables (estimate ↔ proposal ↔ Q&A) are claims too.
5. **Files.** Every file written: (a) the original still untouched,
   (b) `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py office-diff <original> <copy>`
   shows only the intended cells/paragraphs/slides changed and
   `identical_formatting` is true (or every formatting change was intended
   and is named), (c) `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py office render <copy> <dir>`
   and look at every image — overflow, fonts, colours, merged cells, images,
   shapes; .xlsx written through a library → `brse.py office check <copy>` too.
   Diagrams: `brse.py drawio-tool check` passes and the image-only reader test
   passes — see the `diagram` skill.
   Text in another language: `brse.py lang-lint` with zero errors; a translated
   Office copy: `brse.py translation-check` passes (the Stop hook enforces it).
5b. **Final check on the file itself — enforced.** For every deliverable file
   (.xlsx / .docx / .pptx / .drawio) run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py gate check <file> [--original <the file it was copied from>] [--kind estimate-cell|text]`.
   It reads the text from the file (never from a copy you made), pairs each
   cell with the cell beside it, adds the user's words from this session, the
   feedback log, conventions and glossary, and gets it reviewed. When it says
   so, dispatch the `wording-reviewer` agent with exactly the prompt it prints —
   the answer is captured by the plugin; never write it yourself. Answer every
   issue with `brse.py gate resolve` (fixed after you changed the cell, or
   rejected with a reason), run `gate check` again until it passes, and paste
   its `summary` into the hand-back. The Stop hook refuses to end the turn while
   a file changed in this session has no valid stamp; editing a file after it
   passed voids the stamp.
   Text that is not a file (your reply): `brse.py wording run <text file>`
   as before.
6. **Independent rubric review.** Save the user's request, the work (or its
   key parts) and the source excerpts it relies on to files and run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py judge run <request> <work> <sources>`.
   It scores correctness, completeness, logic, evidence, language and scope
   against thresholds.
   - A second model answered → its verdict is final input: every failed
     criterion and every `must_fix` item is fixed (then judge again, at most
     2 more rounds) or explained to the user.
   - `provider: none` → dispatch the plugin's `reviewer` agent with exactly the
     prompt it prints, then run the same `judge run` again; the answer is
     captured by the plugin, never written by you. Say the review was not
     model-independent.
   Never send credentials or more client data than the review needs.
7. **Lint.** Run `verify-output` on the reply draft.

## Output (appended to the handoff reply)

**Checked:** request ✓/✗ · feedback n/n done · sources read x / not read y ·
claims verified n/n · files diffed + rendered ✓/✗ · language lint ✓/✗ ·
rubric <provider>: correctness n, completeness n, logic n, evidence n,
language n, scope n — pass/fail · lint ✓.

Any ✗ that is not fixed → say it first, before the rest of the handoff.
