# Changelog

## 1.1.0 — 2026-08-21

### Added
- **`testcase-review-jp`**: review a test case list (単体テスト仕様書) against
  its Detail Design doc — analyze the design into sourced rules, check every
  test case row against them (✅/⚠️/❌/🔁), report only the flagged rows with
  citations on both sides.
- **`e2e-test-playwright`**: execute test cases against a live app via a
  Playwright MCP server, sequential by default, evidence (screenshot) on
  every case, mandatory screenshot + description for every NG, credentials
  never written to `memory/`/`documents/`.
- `/brse-toolkit:init` now also scaffolds `documents/README.md` (previously
  only `templates/` and `memory/` got a placeholder).
- `/brse-toolkit:init` seeds `memory/glossary.md` with a 56-term common
  IT/BrSE starter vocabulary (EN/VI/JP) instead of an empty schema-only file.
  **Migration note**: this changes the glossary entry format from
  `- <term JP> → "<translation VI>"` to `- EN: <term> | VI: <term> | JP: <term>`
  — a project already initialized under 1.0.0 with real entries in the old
  format will have those entries stop matching in `check-glossary.py` after
  upgrading; migrate existing entries to the new format by hand (or leave
  them, they simply won't be found — nothing crashes).
- Every `SKILL.md`'s shared "Before running" gate now says what a subagent
  dispatched by a main agent should do (skip the stop-and-ask — the parent
  already resolved it) instead of only covering direct/interactive invocation.
- `cross-check`'s Excel-vs-Excel path documents the key/value conversion
  algorithm explicitly (no script did this before — it was reinvented ad hoc
  each time); `diff-structured.py` now warns when a source has a duplicate
  key instead of silently keeping only the last occurrence.
- `image-analyze` now says what to do when `tesseract`/a language pack is
  missing (tell the user, fall back to vision-only) instead of nothing.
- `report-gen`'s concrete flow now covers Excel/Word shapes explicitly
  (previously written for slides only, despite the skill covering all three
  formats).
- `detail-design-jp` distinguishes "該当なし" (genuinely not applicable) from
  "未確認" (applicable but not yet confirmed) — previously conflated.
- `verify-output` documents a `(nguồn: chat khách, <ngày>)` tag for
  requirements sourced from a live conversation (not a file), clarifies the
  lint script only checks a source tag is *present* (not that it's a real,
  well-formed citation), and recognizes Japanese sentence boundaries (。！？)
  so JP-language deliverables (DD docs, JP-target translations) are checked
  correctly instead of being read as one glued, unpunctuated blob.

### Fixed
- `extract-cells.py` crashed (`TypeError`) on any Excel cell containing a
  date/time value.
- `extract-cells.py` silently dropped formula cells with no cached value
  (a file never opened/recalculated by Excel/LibreOffice) — indistinguishable
  from a genuinely empty cell. Now reported with the raw formula + a warning.
- `extract-images.py` always named extracted images `.png` regardless of
  their real format, mislabeling e.g. embedded JPEGs.
- `check-glossary.py` crashed (`FileNotFoundError`) when `memory/glossary.md`
  didn't exist yet, instead of treating it as "no terms confirmed yet".
- `check-glossary.py` parsed the glossary file's own schema-example line
  (`- EN: <term> | VI: <term> | JP: <term>`) as a bogus real entry.
- `lint-hedge-words.py`'s missing-source check only scanned Markdown bullet
  lines — a concluding claim written as a plain paragraph sentence, with no
  source, passed silently (`ok: true`). Now checked the same way bullets are,
  with code fences/headers/tables/horizontal rules/questions/fragments
  correctly excluded from the check.

### Testing
Every skill in the toolkit was re-verified this release by running it in a
fresh, context-isolated agent against a realistic task (built from synthetic
fixtures where no real client document was available) — not just re-read for
structure. All findings above came from those runs, not from inspection alone.
