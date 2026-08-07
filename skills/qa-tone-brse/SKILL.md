---
name: qa-tone-brse
description: Answer Q&A for clients/devs via chat/ticket tools or an Excel Q&A list, in the right tone for each channel. Also manages the QA log directly inside the Excel file sent to the client.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"

## Trigger

Need to answer a question from the client or a dev — via a chat/ticket tool
(Backlog, Redmine, Chatwork...) or by writing into the answer column of an
Excel Q&A list.

## Before answering — mandatory

1. Read `memory/parties.md` — determine which party is asking, which party will
   read the answer. Apply the relay model: do NOT carry the original question's
   pronouns verbatim into the answer if the reader is a different party — use
   the specific party's name, or the neutral Vietnamese "chúng tôi"/"quý vị".
2. If the answer will be written into an existing Excel Q&A list file: run
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/excel-analyze/scripts/extract-cells.py
   <path/to/qa-list.xlsx>` to read back every existing question/answer.
3. Compare the new question against existing ones (simple text similarity — same
   intent, not necessarily same wording). If it matches a question already
   answered → return the existing answer, do NOT compose a different one on
   your own.

## Tone per channel

- **Chat/ticket tool**: concise, straight to the answer, moderate politeness
  level, no email-style opening/closing.
- **Excel Q&A list**: one notch more formal, since it's an official record.

Both channels share `memory/glossary.md` for terminology — don't invent new
wording.

## Batch processing (multiple independent units)

Multiple independent Q&A items in the same request (e.g. "answer these 10
questions in this Q&A list") → dispatch in parallel (spec section 11), one
subagent per question. Each subagent reads `memory/parties.md` +
`memory/glossary.md` itself before drafting. The main agent aggregates results,
dedupes newly-found terms/decisions, then asks the user once, and writes to the
Q&A list file in one pass. **Subagents never write to `memory/` themselves.**

## After answering

- An uncertain answer → label it "chưa xác nhận được, cần hỏi khách" (the
  `verify-output` policy — run
  `${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py` on
  the draft before sending), don't guess at the client's intent.
- If this answer is a new decision not yet in `memory/decisions-log.md` → ask
  the user whether to save it, then write it immediately (don't delay — see the
  CLAUDE.md rule).
