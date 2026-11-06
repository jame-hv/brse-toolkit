---
name: jp-vi-translate
description: Use this when the user asks to translate between Japanese, Vietnamese and English — emails, chat/Q&A messages, spec passages, whole documents or sheets, or fixed terminology — with glossary terms enforced, formatting kept, and a second check when one is available.
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

Text must be translated between Japanese, Vietnamese and English (the pairs
in `config.translation.pairs`): emails, chat/Q&A messages, spec passages,
whole documents or sheets, fixed terms.

## Step 0 — Scope and form

- **Restate**: source → target language, the reader, the form of the result
  (reply text, a translated copy of the file, extra columns in a sheet).
  Target language unclear → ask.
- **Files are never translated in place**: write a copy in
  `config.paths.outputs`, keeping the original's formatting (fonts, colours,
  merged cells, images, shapes) — via `report-gen`'s rules for writing files.
- **Bilingual sheets**: put the translation as a complete table beside the
  source table (same rows, same column order), never alternating source /
  target columns.

## Translating a file (docx / xlsx / pptx)

Never write a script for this — use the plugin's tools:

1. `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/office-text.py extract <file> --max-chars 6000`
   → every translatable unit with a stable id (body, tables, text boxes,
   headers, footers, slide notes, string cells), `duplicates` (translate once,
   reuse), `parts` (chunks for long documents) and `mixed_formatting`.
2. Glossary check on the full text (below), then translate **part by part**,
   each part as a `{id: text}` JSON:
   - `mt.py` per part when an engine exists, then post-edit; otherwise
   - the plugin's `translator` agent (pass the part JSON, languages, reader,
     register and the glossary entries that apply). Same glossary and register
     for every part; table-of-contents entries reuse the heading translations.
3. Merge the parts into one translations JSON and run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/office-text.py apply <file> <translations.json> <out copy>`.
   `untranslated` must be empty (or every remaining id justified, e.g. codes).
4. `office-diff.py <original> <copy>`: only text changed, `identical_formatting`
   true; `office.py render <copy> <dir>` and look at every page/slide —
   overflow from longer text, fonts, line breaks. Paragraphs listed in
   `mixed_formatting` (a bold word inside a sentence) → check them on the
   image and fix emphasis by hand where it matters.

## Before translating any passage

1. Read `.brse/memory/long/parties.md` — who is speaking, who the translation
   is for (relay model, spec section 2).
2. Save the source text to a file, then run `<py> ${CLAUDE_PLUGIN_ROOT}/skills/jp-vi-translate/scripts/check-glossary.py <text_file>
   .brse/memory/long/glossary.md` (the first argument is a file path, not the text itself) — use the settled
   translations verbatim.
3. A term not in the glossary → translate it tentatively and list it as
   "not in the glossary yet — translated as X, needs confirmation". Common IT
   terms: `${CLAUDE_PLUGIN_ROOT}/config/starter-glossary.json` is a hint, not a
   decision.

## Translating

1. Read the whole passage first for its **purpose**; translate by meaning, not
   clause by clause. Don't follow the source's sentence boundaries, don't
   translate softening filler (というか / ということです) literally (spec
   section 6.6 — tested: the old 2-pass model did worse than plain MT).
2. **Same density as the source.** A terse sheet cell stays a terse noun
   phrase; a one-line bullet stays one line. Don't expand, explain or add.
3. **Unchanged**: IDs, codes, file / class / function names, URLs, numbers,
   units, dates. Afterwards compare every number and name in the target with
   the source — they must be identical.
4. **Register** (relay model): the source's first person (私たち) becomes the
   specific party's name when relaying to another party. Relationship not yet
   confirmed in `parties.md`:
   - VI target → neutral formal "chúng tôi" / "quý vị"; never pick em/anh/chị
     on your own.
   - JP target → generic honorific placeholders (お客様, 貴社, 御社,
     ご担当者様, 各位...) follow `config.style.honorific_placeholders`:
     `"allow"` → use them normally; `"avoid"` → only (a) the confirmed party
     name, or (b) drop the addressee noun (e.g. "ご確認をお願いいたします").
     A project's `conventions.md` overrides both.
   - Don't stop to ask who the recipient is just to pick a register on a draft;
     translate with the defaults and add one line noting the register may need
     adjusting once the recipient is confirmed. Ask only when the user is about
     to send it and the register matters.
5. Words added only for grammar (no source token) → mark them `[...]` in the
   review copy so they don't pass as sourced.
6. **Natural target language**: read the result as a native reader would. A
   sentence that only makes sense if you know the source → rewrite it.

## Machine translation base layer and second check

1. **Base layer**: save the source to a file and run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/mt.py <text_file> --from <src> --to <dst>`.
   `engine` is `deepl` / `openai` → start from that translation and post-edit
   it (register, glossary terms, density, naturalness — the rules above).
   `engine` is `none` → translate yourself and say in the output that no
   machine engine was available (the `tried` list says why).
2. **Second check**: write a prompt with the source and your translation,
   asking to back-translate the key passages (decisions, numbers, conditions)
   and list meaning differences, then run
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/ask-agent.py <prompt_file>`. Fix or list
   every difference it reports. `provider` is `none` → use a Claude subagent
   with no other context and say the check was not model-independent.

## Checks on the result (always)

- `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/lang-lint.py <translated text file> --lang <dst> --source-lang <src>`:
  zero errors (untranslated source-script characters, half-width kana);
  warnings (です/ます vs だ/である mix, width mix, long sentences) fixed or
  justified.
- Rubric review: `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/judge.py run <request> <translation> <source excerpt>`
  (second model when available; otherwise run the plugin's `reviewer` agent
  on the printed prompt and `judge.py parse` its reply). `language` and
  `correctness` must pass; fix every `must_fix` item.

## Batch processing

Several independent emails / passages → one subagent per unit (spec section
11); one long email stays in one context so tone and forms of address stay
consistent. Each subagent reads `parties.md` + `glossary.md` itself. The main
agent merges, dedupes new terms, asks the user once. **Subagents never write
to `.brse/memory/` themselves.**

## After finishing a document

1. Run `${CLAUDE_PLUGIN_ROOT}/skills/jp-vi-translate/scripts/check-consistency.py`
   on the `{term, translation_used}` list used in the document; fix any
   `conflicts`.
2. New terms the user confirms → write them to
   `.brse/memory/long/glossary.md` immediately.

## Output

The translation (or the path of the translated copy), then:
- **Key facts** — decisions, numbers, conditions, with their source, placed
  after the translation, not inside it.
- **Terms not in the glossary yet** — tentative translations to confirm.
- **Checks run** — numbers/names compared, consistency script, second check.

Run `verify-output` on the notes section.

## Handoff

Finish with `review-gate` — it runs `verify-output` as its last step.
