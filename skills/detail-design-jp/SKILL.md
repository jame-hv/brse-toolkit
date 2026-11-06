---
name: detail-design-jp
description: Use this when the user needs a Detail Design document written, following the standard Japanese SI framework or the client's own template. Content is pulled from code-to-business output + decisions-log.md, never invented from scratch.
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

## Content sources (spec section 6.11)

- Content comes from `code-to-business` (when writing a DD from existing code) +
  `.brse/memory/long/decisions-log.md` (settled decisions/requirements) — NEVER invent
  technical content.
- Before trusting existing DD content (when updating an old DD) — check
  `.brse/memory/long/decisions-log.md` first, the DD may not yet reflect the latest QA
  decision.

## Template

Two different kinds of template, don't confuse them (spec section 7):

- **Client's own template** — lives in the `config.paths.templates` folders of the **current project
  directory** (where Claude Code is running). If present → use it instead of the
  default framework, keep the structure the client is used to.
- **Default framework bundled with the plugin** — if no client template exists,
  use `${CLAUDE_PLUGIN_ROOT}/skills/detail-design-jp/templates/detail-design-jp-template.md`
  (standard Japanese SI framework: 改訂履歴, 概要/目的, 処理概要+フロー, 画面レイアウト+項目定義,
  入力チェック, テーブル定義, エラー処理). This file is NOT in the project directory —
  don't look for it in the project's template folders.

## Completeness

Every section in the framework must have content or an explicit marker — a
section must NEVER be silently left blank without explanation. Two different
situations need two different markers, don't conflate them:

- **"該当なし"** (not applicable) — only when the source itself states the
  feature/behavior genuinely doesn't exist for this screen (e.g. "no
  delete/add processing on this screen" stated in the requirement).
- **"未確認"** (not yet confirmed) + a specific follow-up question — when the
  section is clearly applicable but the source (code-to-business output /
  decisions-log.md) simply doesn't say (e.g. DB table/column definitions,
  required-field flags, or an error-handling behavior never specified).
  Writing "該当なし" here would be a false claim that the feature doesn't
  exist; leaving it blank hides that it needs an answer — "未確認" plus a
  concrete question is what "never invent technical content" actually
  requires in this case, not a guess and not silence.

## Output

Export the file via `report-gen` (Word/Excel in the format the client uses).

## Before answering

Apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on the
draft response before sending.
