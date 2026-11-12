---
name: test-design
description: Use this when test cases must be designed from a spec, detail design or user story (already converted with doc-to-md) — choosing test techniques per requirement, building a traceable test case list with expected results that a tester or Playwright run can execute, and showing coverage gaps.
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

After the documents are in Markdown (`doc-to-md`) and before execution
(`e2e-test-playwright`). For reviewing an existing test case list against a
design, use `testcase-review-jp` instead.

## Steps

1. **Restate scope**: feature / screens, test level (unit / integration /
   system / E2E / regression), reader, output language and file format
   (client template in `config.paths.templates` first; else the layout below).
2. **Requirement list with IDs.** From `.brse/knowledge/docs/` extract every testable
   statement: input fields with types/limits, business rules, messages, state
   changes, permissions, screen transitions, non-functional limits. Give each
   an ID (`REQ-<screen>-<n>`) and cite the source file + heading/sheet/row.
   Anything ambiguous → a Q&A item (`要確認`), not a guessed expected result.
3. **Pick the technique per requirement — say why:**

   | Requirement shape | Technique |
   |---|---|
   | Input with ranges / lengths / formats | Equivalence partitioning + boundary values (min-1, min, max, max+1, empty, type-wrong) |
   | Several conditions → different outcomes | Decision table (one case per meaningful column) |
   | Object with statuses (order, account lock, approval) | State transition: every valid transition + key invalid ones |
   | Many independent parameters (browser × role × option) | Pairwise, not full combination |
   | User journey across screens | Use-case / scenario: main flow + each alternative/exception flow |
   | Concurrency, 排他制御, double submit | Explicit two-session cases |
   | Messages, labels, layout | Checklist against the spec text, exact wording |

   Always add: required-field empty, permission/role negatives, error
   message wording, back/refresh/double-click, and data persistence after reload.
4. **Write the cases.** One row = one verifiable result. Columns:
   `No | REQ ID | 観点/Viewpoint | Precondition | Test data | Steps | Expected result | Priority (H/M/L) | Technique | Automatable (Y/N) | Result | Remark`.
   Steps are concrete actions on named UI elements (so `e2e-test-playwright`
   can drive them); expected results quote the spec wording, never "works
   correctly". Test data are real values, including the boundary values.
5. **Traceability + coverage.** A matrix REQ ID → case Nos; list every
   requirement with zero cases and every case with no REQ (remove or justify).
   Count cases per technique and per priority.
6. **Self-review** with the `reviewer` agent role: duplicates, untestable
   expected results, missing negatives. Fix, then hand off.
7. **File**: Excel via the toolkit's xlsx scripts (`excel-analyze` /
   `report-gen`) into `config.paths.outputs`; never overwrite a client file.
   Human-readable text for the client (観点, expected-result wording in
   Japanese/Vietnamese) goes through the translator role (Comtor) per the
   project's translation config.

## Output

Test case file path, counts (cases, per priority, automatable), the coverage
gaps and the Q&A list inline.

## Handoff

`testcase-review-jp` (optional second check) → `e2e-test-playwright` for
execution → `report-gen`. Finish with `review-gate`.
