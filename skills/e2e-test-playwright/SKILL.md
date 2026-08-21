---
name: e2e-test-playwright
description: Use this when the user needs test cases actually executed against a running app via a Playwright MCP server (browser_navigate/browser_click/browser_snapshot/browser_take_screenshot-style tools) — not read or reviewed, but driven step by step with evidence captured per case and a screenshot + description on every failure.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"
- Running as a subagent dispatched by a main agent (spec section 11 batch processing) → the main agent has already resolved this gate before dispatching — do not re-trigger the stop-and-ask, proceed directly. Only apply the check above when invoked directly with no parent agent to have already cleared it.

Also confirm the Playwright MCP server's tools are actually loaded/available before starting — don't assume the tool names, check the real list first (exact names vary by server version, but the core set is normally `browser_navigate`, `browser_click`, `browser_type`, `browser_snapshot`, `browser_take_screenshot`, `browser_wait_for`, `browser_console_messages`, `browser_handle_dialog`).

## Trigger

Test cases need to be **run** against a live app (local/staging), not just
read or graded on paper. If the ask is "is this test case list correct/does
it match the design" with no live app involved, that's `testcase-review-jp`,
not this skill — chain to it first when both are needed (see below).

## Step 0 — Scope and safety, before touching the browser

1. Get the target URL/environment from the user or `memory/`. Get login
   credentials **from the user each run** (or from a project-local file the
   user points to that is already outside git, e.g. `.env`) — **never**
   invent, guess, or reuse credentials seen elsewhere, and **never write
   credentials into `memory/*.md`, the result copy, or any evidence file**:
   everything under `memory/` and `documents/` is project-persistent content
   meant to be committed (spec section 3), so a credential written there
   becomes a secret leaked into git history. If the user wants credentials
   reusable across runs, tell them to keep it in an untracked file
   (`.gitignore`d) and point this skill to it each time — this skill itself
   never creates that store. Environment not explicitly confirmed as
   local/staging → ask before running; never run against a production URL
   without the user explicitly confirming it's intentional (E2E runs can
   create/modify real data).
2. Get the test cases: read the test case list with `excel-analyze`
   (`extract-cells.py`), or take a list the user pastes directly. Column
   layout mirrors `testcase-review-jp` — precondition / steps / expected
   result, whatever the client's own header names are.
3. Rows already marked ⚠️/❌/🔁 by `testcase-review-jp` → don't execute them
   as if the expected result were trustworthy ground truth. Flag them back to
   the user and ask whether to run anyway (recording against what the test
   case currently says) or fix the row first.

## Step 1 — Execute one test case

For each row, in order:

1. **Set up the precondition** — `browser_navigate` (and any setup actions)
   to reach the state the row's precondition column describes.
2. **Run the steps** — translate each numbered step in the procedure column
   into the matching tool call (`browser_click`, `browser_type`,
   `browser_select_option`, `browser_press_key`, ...). Use `browser_snapshot`
   (accessibility tree) to locate elements precisely before acting on them —
   don't act on an element only guessed from a screenshot; screenshots are
   evidence, not the input for locating things (same precise-extraction-
   over-vision principle as `excel-analyze`).
3. **Check the expected result** — read actual page state via
   `browser_snapshot`/`browser_evaluate` (or `browser_console_messages` /
   `browser_network_requests` when the expected result is about an error
   message or a request, not visible text) and compare literally against the
   row's expected-result column. Don't mark a result OK from a plausible
   guess — if the check can't be performed with the available tools, mark
   PENDING with the reason, never guess OK.
4. **Capture evidence** — once the result of that row is known (OK/NG/
   PENDING/CANCEL), `browser_take_screenshot` **every** case, pass or fail,
   saved as `documents/e2e-evidence/<run-id>/TC<No>_<result>.png` (e.g.
   `TC059_NG.png`; create the directory if missing; `<run-id>` = date +
   screen/feature name, so repeat runs don't overwrite each other). The test
   case No. in the filename is the join key back to the row — it's what lets
   the remark column and the evidence folder be cross-referenced without
   opening both side by side (see Step 2). A dialog blocks the browser →
   `browser_handle_dialog` to clear it, don't leave the run stuck.

An unexpected native dialog or a step that can't be completed at all with the
available tools (e.g. a native OS file picker) → stop that case, mark
PENDING with the reason, move to the next case — don't skip silently and
don't force a workaround that isn't what the step actually says.

## Step 2 — Record the result

Use the same OK/NG/PENDING/CANCEL vocabulary the test case sheet itself
already tracks (総項目数/OK項目数/NG項目数/PENDING項目数/CANCEL項目数, when
present) rather than inventing a new one.

- **OK**: expected result observed exactly as written.
- **NG**: expected result NOT observed — the row's remark/備考 field must
  state, in one or two sentences: what was expected (quote the row) vs what
  was actually observed, plus the evidence file's exact name
  (`TC<No>_NG.png`). This is the bug-description ↔ screenshot mapping: the
  No. is the shared key, present in both the Excel row and the filename — a
  reviewer must be able to find the right screenshot from the remark text
  alone, without guessing. A failure without both the screenshot and this
  description is not a complete result — don't record NG without them.
- **PENDING**: couldn't be verified with available tools (see Step 1.3) —
  state why.
- **CANCEL**: precondition from an earlier case failed, making this case
  unreachable — reference the blocking case's No.

Write results into a **copy** of the test case file, never the client's
original (same rule as `testcase-review-jp`) — confirm the target file/copy
with the user before writing.

## Sequential by default

Unlike most brse-toolkit skills, this one does **not** default to parallel
subagent dispatch (spec section 11) — each row's precondition usually depends
on the app state the previous row left behind, and two subagents driving the
same browser/session would corrupt each other's state. Run rows in order.
Parallelize only when the user confirms a specific batch of rows is
state-independent (e.g. read-only checks replayed from the same fixed URL),
and then use one isolated browser tab/context per subagent, never a shared one.

## Output

A run summary (counts per OK/NG/PENDING/CANCEL) + the filled-in result copy +
the evidence folder. List every NG/PENDING row inline in the response too —
don't make the user open the file to find out what failed.

## Before answering

Apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on
the draft response. Every NG's description is a factual claim about observed
behavior — cite the evidence file: `(nguồn: documents/e2e-evidence/<run-id>/TC<No>_NG.png)`.
