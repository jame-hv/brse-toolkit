---
name: jp-vi-translate
description: JP-VI translation. Fixed fields/terminology use the glossary script; prose/email/QA are translated by meaning + relay model, NOT the pass-1-literal/pass-2-naturalize model.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"

## Before translating any passage

1. Read `memory/parties.md` — who is speaking, who the translation is for
   (relay model, spec section 2).
2. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/jp-vi-translate/scripts/check-glossary.py <text>
   memory/glossary.md` — get the terms already settled, use that exact
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
   `memory/parties.md` → default to the neutral Vietnamese pronouns "chúng
   tôi"/"quý vị" ("we"/"you", formal register), don't pick an informal register
   (em/anh/chị) on your own.
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
`memory/parties.md` + `memory/glossary.md` itself before translating. The main
agent aggregates the translations, dedupes newly-found terms, then asks the
user once with one combined list. **Subagents never write to `memory/`
themselves.**

## After finishing a document

Run `${CLAUDE_PLUGIN_ROOT}/skills/jp-vi-translate/scripts/check-consistency.py`
on the `{term, translation_used}` list applied in the document — if there are
`conflicts`, fix them for consistency before answering.

New terms confirmed while translating → write them to `memory/glossary.md`
immediately (don't delay, see the CLAUDE.md rule).

## Before answering

Apply `verify-output` — run
`${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on the
fact-check/notes section attached to the translation before sending.
