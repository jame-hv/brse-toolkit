---
name: detail-design-jp
description: Use this when the user needs a Detail Design document written, following the standard Japanese SI framework or the client's own template. Content is pulled from code-to-business output + decisions-log.md, never invented from scratch.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"
- Running as a subagent dispatched by a main agent (spec section 11 batch processing) → the main agent has already resolved this gate before dispatching — do not re-trigger the stop-and-ask, proceed directly. Only apply the check above when invoked directly with no parent agent to have already cleared it.

## Content sources (spec section 6.11)

- Content comes from `code-to-business` (when writing a DD from existing code) +
  `memory/decisions-log.md` (settled decisions/requirements) — NEVER invent
  technical content.
- Before trusting existing DD content (when updating an old DD) — check
  `memory/decisions-log.md` first, the DD may not yet reflect the latest QA
  decision.

## Template

Two different kinds of template, don't confuse them (spec section 7):

- **Client's own template** — lives in `templates/` of the **current project
  directory** (where Claude Code is running). If present → use it instead of the
  default framework, keep the structure the client is used to.
- **Default framework bundled with the plugin** — if no client template exists,
  use `${CLAUDE_PLUGIN_ROOT}/skills/detail-design-jp/templates/detail-design-jp-template.md`
  (standard Japanese SI framework: 改訂履歴, 概要/目的, 処理概要+フロー, 画面レイアウト+項目定義,
  入力チェック, テーブル定義, エラー処理). This file is NOT in the project directory —
  don't look for it under `templates/`.

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
