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
4. **Evidence.** Every conclusion has a ref (inline `file:line` /
   `Sheet!A1`, or `config.style.source_tag`). Numbers that appear in more
   than one place (estimate ↔ proposal ↔ Q&A) are equal everywhere.
5. **Files.** Every file written: (a) the original still untouched,
   (b) `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/office-diff.py <original> <copy>`
   shows only the intended cells/paragraphs/slides changed and
   `identical_formatting` is true (or every formatting change was intended
   and is named), (c) rendered to an image and looked at — overflow, fonts,
   colours, merged cells, images, shapes.
6. **Independent review.** Write a short review prompt — the user's request,
   the restatement, the result (or the key parts of it), and the question
   "what is wrong, missing, unsupported or out of scope?" — to a file and run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/ask-agent.py <prompt_file>`.
   - `provider` is a real agent → take each point seriously: fix it, or say
     why it doesn't apply.
   - `provider` is `none` → dispatch a Claude subagent with the same prompt
     and no other context, and say the review was not model-independent
     (and why — the `tried` list).
   Never send credentials or more client data than the review needs.
7. **Lint.** Run `verify-output` on the reply draft.

## Output (appended to the handoff reply)

**Checked:** request ✓/✗ · feedback n/n done · sources read x / not read y ·
files diffed + rendered ✓/✗ · second review: <provider> — <points fixed /
rejected with reason> · lint ✓.

Any ✗ that is not fixed → say it first, before the rest of the handoff.
