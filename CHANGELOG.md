# Changelog

## 2.2.0 — 2026-11-06

### Changed
- Diagram acceptance keeps only checks with a stated reason: purpose in the
  title, one connected story (no island of boxes), every box and arrow
  sourced and its quote verified, computed or template positions, no
  overlapping or dangling elements, and the image-only reader test. Made-up
  limits (box count, label length) and the "one kind of view" rule are gone;
  those facts are reported for the reader test instead.
- The kind of diagram is chosen from the question it must answer; a template
  is used only when `drawio-tool.py suggest` measures that it already has the
  needed icons (`catalog` reads every bundled template).
- The agent never asks the user how to draw; it chooses, draws, checks and
  states the reason.

### Fixed
- `drawio-tool.py kinds` no longer lists hand-placed layout.

## 2.1.0 — 2026-11-06

From real use on an estimate project, where the diagram of the current system
and the analysis could not be understood by the reader.

### Added
- **Diagram acceptance criteria** — `drawio-tool.py check` (purpose, one view
  per diagram, every quote verified in its source, computed or template
  positions, readability, drawn changes equal to the change table) and
  `drawio-tool.py reader-test` (a reviewer that sees only the image must say
  who does what, in which order, and what changes).
- **Diagrams built from sources** — `build` takes swimlane (lane = who,
  column = step order) or automatic layered layout, never hand positions;
  non-cloud kinds (system, device, equipment, actor, datastore, file, step…);
  changed / new / removed / unconfirmed with a generated legend; every box and
  arrow carries its source or is drawn as unconfirmed; a sources table next
  to the diagram; icons can be taken from another diagram or template.
- **Sentence-by-sentence wording review** — `wording.py` and the
  `wording-reviewer` agent: every sentence or label read by someone who did
  not write it, each problem returned with a rewrite; the project's rejected
  sentences are the standard. Runs on deliverables and on replies.
- **Reader criterion** in the rubric; rules for writing for the reader, no
  abbreviations, keeping the document's own terms and separating "the
  document says" from "my reading", no invented examples.
- **API keys in the git-ignored `.brse/config.local.json`**, never printed;
  a hook refuses tool calls that open key files.

## 2.0.0 — 2026-11-06

**Breaking:** workspaces now live under `.brse/`, and `/brse-toolkit:init`
asks questions instead of copying a fixed template. Existing 1.x workspaces
(`memory/` at the project root) are offered a migration on the next
`/brse-toolkit:init`; nothing moves without a yes.

### Added
- **Per-workspace JSON config** — `config/defaults.json` <
  `~/.config/brse-toolkit/config.json` < `.brse/config.json`, merged by
  `scripts/brse-config.py`: warns on unknown keys, reports JSON errors by
  line, refuses secret values (config names environment variables only).
- **`/brse-toolkit:doctor`** — read-only report of Python, packages, office
  CLIs, draw.io, OCR, LibreOffice, second-agent CLIs, with the install
  command for this OS (`config/dependencies.json`).
- **`/brse-toolkit:setup`** — Python packages into a private venv
  (`runtime.python`), optional tools only with a yes per item, office CLIs
  located inside installed apps and recorded in `tools.paths`.
- **New project CLAUDE.md block** from `init`: deliverables table, folder map,
  skill routing table, and 10 working rules that each show up in the reply
  (restatement, sources read / not read, evidence, scope, feedback ledger,
  checks before handoff, client-file safety, writing density, memory,
  handoff format).
- **Plugin-level tests** (`scripts/tests/test_plugin_structure.py`) and the
  first behavior eval (`evals/init-creates-workspace`).

- **Memory by hooks** — `SessionStart` injects project, conventions, recent
  correction categories and the previous session; `Stop` / `PreCompact` write
  `.brse/memory/short/<date>-<session>.md` from the transcript (computed,
  idempotent, pruned by retention). `/brse-toolkit:memory-review` promotes
  approved items to long-term memory; `feedback-log.md` +
  `scripts/feedback-stats.py` measure corrections by category.
- **Knowledge base** — `scripts/kb-ingest.py` (xlsx incl. hidden sheets,
  docx, pptx incl. notes, pdf via pdftotext, text incl. cp932) →
  `.brse/knowledge/docs/*.md` + `manifest.json` (ok / partial / unreadable,
  what needs visual reading) + SQLite FTS5 trigram index;
  `scripts/kb-search.py` (substring fallback for 1–2 character Japanese
  queries); `/brse-toolkit:ingest`.
- **Second agent and machine translation** — `scripts/ask-agent.py` (codex
  read-only / gemini / OpenAI API, falls back to "none" with reasons) and
  `scripts/mt.py` (DeepL / OpenAI).
- **New skills** — `review-gate` (mandatory final check: request vs result,
  feedback ledger, coverage, evidence, office-diff + render, independent
  review, lint), `diagram` (draw.io from existing diagrams, export and
  inspect), `estimation` (logic chain from inputs to every number,
  preconditions / not-included rules, verified totals).
- **`scripts/office-diff.py`** — before/after comparison of xlsx / docx /
  pptx: changed values, cells whose formatting changed, merges, images.
- **Personal library** — `scripts/library.py` + `/brse-toolkit:library` for
  approved deliverables reused across projects.
- Workspace `layout_version`; session start warns about 1.x or outdated
  layouts.
- GitHub Actions: pytest on ubuntu / macos / windows.

- **Office tools that use the office CLIs** — `scripts/office.py` (info /
  render / round-trip check through gridcraft / wordcraft / deckcraft, else
  LibreOffice / Python, always saying which) and `scripts/office-text.py`
  (extract every translatable unit incl. headers, footers, text boxes, notes;
  apply translations to a copy keeping formatting; long documents split into
  parts; .xlsx written through the CLI after a passing round-trip check).
- **Measured quality** — `verify-claims.py` (opens the cited cell / line /
  part and compares), `judge.py` + `config/rubric.md` (six criteria with
  thresholds, second model or the `reviewer` agent), `lang-lint.py`.
- **Plugin agents** — `translator` (fixed translation rules, glossary,
  JSON-in/JSON-out for file units) and `reviewer` (rubric JSON).
- **Template-based diagrams** — `scripts/drawio-tool.py`: list and copy draw.io's
  bundled templates (read from its app.asar), edit by id, lint, export (snap
  sandbox handled); `diagram` skill rewritten around it.
- **`scope-analysis`** (requirements, gaps, Q&A), **`approach`** (方針 from code
  and documents), **`/brse-toolkit:estimate-project`** (staged estimate flow).
- **Document origins** — `paths.internal` and `paths.deliverables` next to
  `paths.sources`; knowledge chunks tagged client / internal / delivered;
  `kb-search.py --origin`; `deliverables-log.md`.
- **Sync** — session start compares sources with the manifest, re-ingests a
  few changed files itself, and flags memory entries citing a changed file;
  init ingests right away; manifest keeps the previous sha of each file.
- **`.brse/config.local.json`** — personal, git-ignored layer on top of the
  shared workspace config. Knowledge copies are git-ignored by default.
- **API keys** — plugin `userConfig` (sensitive, OS keychain) and
  `scripts/set-key.py` (`~/.config/brse-toolkit/secrets.env`); scripts read
  env → plugin option → secrets file.

### Changed
- Every skill ends with `review-gate`; analytical skills ingest sources
  first and use the manifest as their file list; `jp-vi-translate` uses the
  MT base layer and a second-agent back-check; `image-analyze` and
  `detail-design-jp` rewritten with steps and checks.
- Nine skills rewritten with explicit steps, output formats and checks
  (brainstorm-brse, research-jp-tech, proposal-gen, report-gen, qa-tone-brse,
  code-to-business, cross-check, excel-analyze, jp-vi-translate). Highlights:
  coverage inventory before any comparison, counts recomputed from both
  sides, end-to-end code tracing, slides with one message each and numbers
  tied to the estimate, rendering output files to images before handoff.
- `jp-vi-translate` covers JA / VI / EN, translates files into copies,
  keeps source density, and verifies numbers and names are unchanged.
- Skills read folders, source-tag format, honorific policy and test status
  vocabulary from config instead of hardcoding them; scripts run with the
  recorded interpreter instead of a hardcoded `python3`.
- Glossary starts empty; the 56 starter terms moved to
  `config/starter-glossary.json` as hints only.
- `pytest` moved to `requirements-dev.txt`; `pytest.ini` disables pytest's
  cache.

### Fixed
- `lint-hedge-words.py` accepted only a literal Vietnamese tag; now takes
  `--source-tag` and accepts inline `file:line` / `Sheet!A1` references.
- `check-glossary.py` matched placeholder cells (`—`) against any text; EN
  terms now match as whole words.
- `cross-check` looked for Vietnamese decisions-log field names that `init`
  never wrote, so reconciliation never matched.
- `jp-vi-translate` told the agent to pass the text itself to
  `check-glossary.py`, which expects a file path.
- Test data derived from real client documents replaced with synthetic data;
  client- and user-specific rules removed from skills.

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
