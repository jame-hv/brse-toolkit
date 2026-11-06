---
name: jp-vi-translate
description: Use this when the user asks to translate text between Japanese and Vietnamese — emails, spec passages, chat/QA messages, or fixed terminology/glossary fields.
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

## Before translating any passage

1. Read `.brse/memory/long/parties.md` — who is speaking, who the translation is for
   (relay model, spec section 2).
2. Save the source text to a file, then run `<py> ${CLAUDE_PLUGIN_ROOT}/skills/jp-vi-translate/scripts/check-glossary.py <text_file>
   .brse/memory/long/glossary.md` (the first argument is a file path, not the text itself) — get the terms already settled, use that exact
   translation, don't invent another wording.
3. A term appears in the text but is NOT in the glossary → flag "not in the
   glossary yet, translating tentatively as X, needs confirmation" — don't
   silently decide on your own.

## Fixed fields/terminology

Use the translation from `check-glossary.py` verbatim. Don't change it.

## Prose / email / QA (spec section 6.6 — actually tested, the old 2-pass model
performed worse than plain machine translation)

1. Read the whole passage to understand the **communicative purpose**, don't
   translate clause by clause.
2. Translate directly by meaning, in the right Vietnamese business register —
   do NOT stick to Japanese sentence/clause boundaries, do NOT literally
   translate tone-softening filler words (というか/ということです).
3. Apply the relay model: the source's first-person pronoun (私たち) → change
   to the specific party's name when relaying to another party, don't translate
   it verbatim. Relationship between parties not yet confirmed in
   `.brse/memory/long/parties.md`:
   - VI target → default to the neutral Vietnamese pronouns "chúng
     tôi"/"quý vị" ("we"/"you", formal register), don't pick an informal
     register (em/anh/chị) on your own.
   - JP target → generic honorific placeholders (お客様, 貴社, 御社,
     ご担当者様, 各位...) follow `config.style.honorific_placeholders`:
     `"allow"` → use them normally; `"avoid"` → only (a) the real party
     name, once confirmed in `.brse/memory/long/parties.md`, or (b) drop the
     addressee noun entirely (Japanese elides the subject when it's clear
     from context — e.g. "ご確認をお願いいたします" instead of
     "お客様に...いただきたく存じます"). Party not confirmed yet → (b).
     A project's `.brse/memory/long/conventions.md` overrides both.
   - Don't stop and ask the user who the recipient/relay chain is just to
     pick a register — on a draft that hasn't been sent anywhere yet, that
     question reads as a non-sequitur. Translate with the defaults above; if
     it's genuinely load-bearing, add one line after the translation noting
     the register may need adjusting once the recipient is confirmed. Only
     ask directly when the user says they're about to send the text and a
     wrong register would actually matter.
4. Fact-check separately: list the key facts/decisions (not every sentence)
   with their source, placed AFTER the translation — don't interleave it
   inside the prose.
5. Words inserted only to make the Vietnamese grammatical (no corresponding
   source token) → mark them clearly (e.g. square brackets `[...]`), don't let
   them blend in as if sourced.

## Batch processing (multiple independent units)

Multiple independent emails/passages in the same request (e.g. "translate
these 20 emails") → dispatch in parallel (spec section 11), one subagent per
email/passage. Within one long email, still translate sequentially in the same
context so tone + forms of address stay consistent. Each subagent reads
`.brse/memory/long/parties.md` + `.brse/memory/long/glossary.md` itself before translating. The main
agent aggregates the translations, dedupes newly-found terms, then asks the
user once with one combined list. **Subagents never write to `.brse/memory/`
themselves.**

## After finishing a document

Run `${CLAUDE_PLUGIN_ROOT}/skills/jp-vi-translate/scripts/check-consistency.py`
on the `{term, translation_used}` list applied in the document — if there are
`conflicts`, fix them for consistency before answering.

New terms confirmed while translating → write them to `.brse/memory/long/glossary.md`
immediately (don't delay, see the CLAUDE.md rule).

## Before answering

Apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on the
fact-check/notes section attached to the translation before sending.
