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

Text must be translated between Japanese, Vietnamese and English (the pairs in
`config.translation.pairs`): an email, a chat / Q&A message, a spec passage, a
whole document or sheet, a list of terms.

## The flow — every step, in this order

`brse.py <command>` below = `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py <command>`.

### 1. Restate (one line each, in the reply)
Source → target language · who wrote the source and who will read the result
(`.brse/memory/long/parties.md`) · the form of the result: reply text, a
translated copy of the file, or the translated table **beside** the source
table in a copy (bilingual sheet). Target language unclear → ask; anything else
→ take the default and say it.

### 2. Load what is already settled
- `.brse/memory/long/glossary.md` — save the source text to a file, run
  `brse.py check-glossary <text_file> .brse/memory/long/glossary.md`; every
  match is used verbatim.
- `.brse/memory/long/conventions.md` — rules the user confirmed (forms of
  address, terms kept in the original, layout).
- A term not in the glossary → translate it and list it at the end as "not in
  the glossary yet — translated as X, needs confirmation"
  (`config/starter-glossary.json` is a hint, not a decision).

### 3a. A passage (email, chat, Q&A, spec excerpt)
Translate it yourself, the whole passage in one go, following *How to
translate* below. Then go to step 4.

### 3b. A file (.xlsx, .docx, .pptx) — never write a script for this
1. `brse.py office-text extract <file> --pictures-dir <dir>` → units, each with an id, its text and
   its **context** (.xlsx: sheet, the nearest filled cell to the left and above
   — the row label and the column header; .docx: the heading it sits under;
   .pptx: the slide). The context decides the meaning: 池 next to 作成者 is a
   person's name, not "pond". Text inside shapes and text boxes is a unit too
   (`<sheet>!drawing<k>/sp<n>/p<m>`). `pictures` lists every picture on a sheet,
   written to `<dir>` (EMF converted to PNG): **open every one** — screen images
   and diagrams often carry labels that must match the translated table, and
   text inside a picture cannot be replaced in the copy.
2. Read the whole document once before translating
   (`.brse/knowledge/docs/<file>.md` after `/brse-toolkit:ingest`, or the units
   in order) — what it is for, who reads it.
3. **One translator for the whole document** (design spec §11: inside one unit
   of work the text is translated in order, in one context, so terms and tone
   stay the same). Dispatch the plugin's `translator` agent once with: the units
   JSON *including context*, languages, reader, register, the glossary entries
   and conventions that apply. A document with several `parts` → the same
   agent gets them one after another (continue it with SendMessage), never one
   agent per part. Units listed under `duplicates` are translated once.
4. Save its answer as `translations.json` and write the copy:
   `brse.py office-text apply <file> translations.json <copy in config.paths.outputs> [--beside | --to-column <letter>]`.
   The sheet already has an empty column for the translation (a bilingual
   estimate) → `--to-column <that column>`; never fill it with your own script.
   In place, the package XML is edited: pictures, EMF, shapes and charts stay
   byte for byte; a translated cell that would be cut off (next cell filled, or
   merged) gets shrink-to-fit (`--keep-cell-style` turns that off); a formula
   that only points at a translated cell shows the translation. `--beside`
   (bilingual sheet) goes through openpyxl and is refused for a file with
   drawings — never pass `--allow-losing-drawings` without the user's yes.
5. **Check, fix, check again** — mandatory, the Stop hook refuses to end the
   turn without it:
   `brse.py translation-check <file> translations.json <copy> --lang <dst> --source-lang <src>`.
   Every problem names a unit: missing translation, changed number, lost code
   or ID, lost formatting marker, glossary term not used, source text left
   untranslated. Fix those units (yourself, or by continuing the same translator
   with the list), apply again, check again until `pass` is true.
6. `brse.py office-diff <file> <copy>` (only text changed, or the beside table
   added) and `brse.py office render <copy> <dir>` — look at every translated
   page: text cut off or spilling over a neighbour, fonts, line breaks, emphasis
   on the right words, cells still in Japanese. Fix and render again.
   A formula computed from translated cells (lookups, arrays) is recalculated
   when Excel opens the copy (`fullCalcOnLoad`); LibreOffice's render may still
   show the old value — say so instead of calling it untranslated.
7. Text inside pictures: give a table *label in the picture → translation*
   (the same words as the translated cells) in the hand-back.

### 4. Read it as the reader, then a second check
- `brse.py wording run <translation text file> --reader "<who reads it>" --lang <dst>`
  (no second model → the plugin's `wording-reviewer` agent on the printed
  prompt, then `brse.py wording parse <reply>`). Apply every rewrite that does
  not change the meaning.
- Key facts (decisions, numbers, conditions, deadlines): write a prompt with the
  source and your translation of those passages asking for a back-translation
  and the meaning differences; `brse.py ask-agent <prompt_file>`. Fix or list
  every difference. `provider` "none" → a Claude subagent with no other
  context, and say the check was not model-independent.

### 5. Hand back
The translation (or the copy's path), then:
- **Key facts** — decisions, numbers, conditions with their source, after the
  translation, not inside it (design spec §6.6).
- **Terms not in the glossary yet** — tentative translations to confirm.
- **Checks** — translation-check result, wording review, second check, what was
  looked at in the rendered copy.
New terms the user confirms → `.brse/memory/long/glossary.md` immediately.
Finish with `review-gate`.

## How to translate (design spec §2 and §6.6)

1. Read for the purpose first; translate by meaning. Don't follow the source's
   sentence boundaries; don't translate softening filler (というか /
   ということです) word for word.
2. Same density as the source: a terse cell stays a terse noun phrase, a
   one-line bullet stays one line. Don't expand, explain or add.
3. Unchanged: IDs, codes, file / class / function names, URLs, numbers, units,
   dates (a date may change format, not value).
4. Relay: the source's first person (私たち) becomes the named party when the
   reader is a different party. Relationship not confirmed in `parties.md`:
   Vietnamese → neutral "chúng tôi" / "quý công ty", never em / anh / chị on
   your own; Japanese → follow `config.style.honorific_placeholders`
   (`"allow"`: お客様, 貴社, ご担当者様…; `"avoid"`: the confirmed party name, or
   drop the addressee). Don't stop to ask the recipient just to pick a register
   for a draft — use the default and say in one line it may need adjusting.
5. A term `conventions.md` says to keep in the original → `「原文」(meaning)`;
   lang-lint and translation-check accept text inside 「」.
6. Words added only for grammar (no source token) → mark them `[...]` in the
   review copy so they don't pass as sourced.
7. Read the result as a native reader would; a sentence that only makes sense
   if you know the source → rewrite it.

## Machine translation

`brse.py mt <text_file> --from <src> --to <dst>` answers only when
`config.translation.engine_order` lists an engine with a key. Its output is a
second opinion for the translator, not the draft to edit — the design spec
§6.6 records that "translate literally, then make it natural" produced
translationese. Which works better on this project's documents is decided by
measuring both on real units, not assumed.

## Several independent texts

Several separate emails / passages → one subagent per text (design spec §11),
each reading `parties.md` and `glossary.md` itself. The main agent merges,
dedupes new terms, asks the user once. Subagents never write to
`.brse/memory/`.
