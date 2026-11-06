---
name: init
description: Set up a brse-toolkit workspace in the current directory — .brse/config.json, 3-tier memory, knowledge folder, and a project CLAUDE.md written from the user's answers
---

Run these steps in the current directory (the user's project directory, NOT the plugin repo).

## 1. Check what already exists

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs. None → tell the user to run `/brse-toolkit:setup`.

Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse-config.py` and read `workspace_root`:
- equals the current directory → already initialized. Stop and ask whether to
  re-run (re-asks the questions below and rewrites `.brse/config.json` and the
  brse-toolkit block of `CLAUDE.md`; memory and knowledge are never touched).
- is a parent directory → this folder is inside another workspace. Say which
  one and ask whether to create a separate nested workspace here.
- `error` → show it and stop; the existing config must be fixed first.

**1.x layout** (`memory/parties.md`, `memory/glossary.md`, ... at the project
root): offer to migrate them into `.brse/memory/long/`. Only with the user's
yes: move them (`git mv` when tracked), drop glossary lines whose source note
is `khởi tạo mặc định` (they were starter terms, not project decisions — the
starter list now lives in the plugin), keep every other line unchanged.

## 2. Look before asking

List the top-level folders and the file types in each (names and counts only —
don't read contents yet). Use this to propose defaults in the questions below
(e.g. a folder full of client .xlsx/.pptx → likely a source folder; a folder
named like "template" → template folder).

## 3. Ask the user (one message, all questions together)

1. Project name.
2. Languages: the client's documents, the internal team, and the language
   replies to the user should be in.
3. Which folders hold source material from the client (propose from step 2).
4. Which folders hold the client's templates, if any.
5. The main deliverables for this project (e.g. estimate, proposal deck,
   detail design, test spec, Q&A list) — and for each one: is it read by the
   client or only internally, and which file format.

Don't guess answers the user didn't give — leave the default and say so.

## 4. Create the workspace

```
.brse/
├── config.json
├── .gitignore            # contents: "memory/short/" and "knowledge/index.sqlite"
├── memory/
│   ├── long/             # parties.md, glossary.md, conventions.md, decisions-log.md, feedback-log.md
│   └── short/            # session logs written by the plugin's hooks
└── knowledge/
    └── docs/             # source documents converted to Markdown
```

`.brse/config.json` holds only what the user answered (everything else is
inherited from the plugin defaults and the user's own config):

```json
{
  "layout_version": 2,
  "project": {
    "name": "<answer 1>",
    "client_language": "<answer 2>",
    "team_language": "<answer 2>",
    "reply_language": "<answer 2>",
    "deliverables": [{"name": "<answer 5>", "reader": "client|internal", "format": "xlsx|pptx|docx|md"}]
  },
  "paths": {
    "sources": ["<answer 3>"],
    "templates": ["<answer 4>"],
    "outputs": "<an output folder — propose `output/`>"
  }
}
```

Never write an API key or any other secret into this file — providers are
configured by environment-variable name only (see the README).

The `memory/long/` files start empty except for their title and schema
(examples are placeholders, never real data):

`parties.md`:
```
# Parties — who is who in this project

Entry schema:
- <Party name> — role: <client/vendor/our team/...> — form of address: <confirmed form, or "not confirmed">
  — source: <where this was confirmed>, <date> — status: active
```

`glossary.md`:
```
# Glossary EN-VI-JP

Entry schema:
- EN: <term> | VI: <term> | JP: <term> — <source note>, <date> — status: active
```

`conventions.md`:
```
# Conventions — formatting and writing conventions confirmed for this project

Entry schema:
- <what, e.g. "red text in sheet X"> → <confirmed meaning or rule> — source: <file or message>, <date> — status: active
```

`decisions-log.md`:
```
# Decisions log — overlay on top of the official spec/design

Entry schema:
- Decision: <content, with its scope stated>
  Source: <QA id / message / meeting>, <date>
  Status in the official doc: <FULLY updated / PARTIALLY updated / NOT YET updated>
  Status: active
```

`feedback-log.md` (filled by `/brse-toolkit:memory-review`):
```
<!-- last-review: never -->
# Feedback log — corrections the user gave, by category

Entry schema:
- <YYYY-MM-DD> | <category> | <correction, one line> | rule: <conventions entry it produced, or none>
Categories: misread-request, did-not-read-source, unsupported-claim, out-of-scope,
ignored-feedback, format-layout, writing-style, translation, wrong-content, other
```

An entry that gets replaced is never deleted: set its `status` to
`superseded by <date>` and add the new entry below it.

Then run `brse-config.py` again: `workspace_root` must be the current
directory, with no `error` and no `warnings`. Fix the config before going on
if not.

## 5. Write the project CLAUDE.md

Write the block below between the markers `<!-- brse-toolkit:start -->` and
`<!-- brse-toolkit:end -->`. If `CLAUDE.md` exists, replace only an existing
block between those markers (or append the block when there is none) — never
touch the user's own content outside it. Fill every `<...>` from the answers
and the folder scan; an answer the user didn't give → write `not set yet`,
never a guess. Deliverable `Language` = the client language for `reader: client`, the team language for `reader: internal` (a rule, not a guess). Keep the block's wording in English as given (it is read by the
agent); only the filled-in values may be in another language.

```markdown
<!-- brse-toolkit:start -->
# <project name>

Client documents: <client language> · Team: <team language> · Reply to the user in: <reply language>

## Deliverables
| Deliverable | Reader | Format | Template | Language |
|---|---|---|---|---|
| <one row per deliverable from answer 5> | <client / internal> | <xlsx / pptx / docx / md> | <template path, or "none yet"> | <language> |

## Where things are
- Client sources: <source folders>. Converted, searchable copies: `.brse/knowledge/docs/`
  (refresh with `/brse-toolkit:ingest`; the manifest lists what could not be read as text).
- Client templates: <template folders>.
- Settled facts: `.brse/memory/long/` — parties, glossary, conventions, decisions-log. Read before any work.
- Recent sessions: `.brse/memory/short/`.
- Settings and available tools: `.brse/config.json`, `/brse-toolkit:doctor`.

## Which skill for which job
| The user asks to… | Use |
|---|---|
| compare two sources, check a sheet/estimate/spec against client documents, find what changed | `brse-toolkit:cross-check` |
| read or check an Excel file (values, colours, images, shapes) | `brse-toolkit:excel-analyze` |
| read a screenshot, diagram or photo | `brse-toolkit:image-analyze` |
| translate (JA / VI / EN) an email, spec, sheet, Q&A | `brse-toolkit:jp-vi-translate` |
| answer a client/dev question, fill a Q&A list | `brse-toolkit:qa-tone-brse` |
| explain business logic from source code | `brse-toolkit:code-to-business` |
| write a detail design | `brse-toolkit:detail-design-jp` |
| review a test case list against the design | `brse-toolkit:testcase-review-jp` |
| run test cases in a browser | `brse-toolkit:e2e-test-playwright` |
| propose options for a problem | `brse-toolkit:brainstorm-brse` |
| research a technology / regulation | `brse-toolkit:research-jp-tech` |
| make a proposal | `brse-toolkit:proposal-gen` |
| produce a report / slide / Word file in the client's format | `brse-toolkit:report-gen` |
| create, revise or check an estimate (見積書, 前提条件) | `brse-toolkit:estimation` |
| draw an architecture / flow / transition diagram | `brse-toolkit:diagram` |
| hand work back (always, last step) | `brse-toolkit:review-gate` |
Several apply → name them in the restatement (rule 1) and chain them.

## Rules — each one is visible in the reply
1. **Restate first.** For any task beyond a one-line answer, open with:
   `Deliverable:` · `Format / file:` · `Sources:` · `Out of scope:`. Anything
   unclear → ask before working. Re-read the user's message once more before
   starting; answer what was asked, not a nearby question.
2. **Read, don't grep.** Read every relevant source in full (all sheets, all
   slides, all pages, including images and shapes). Keyword search only
   locates; it never supports a conclusion. End analytical work with a
   `Sources read:` list and a `Not read:` list (with the reason).
3. **Evidence or "unconfirmed".** Every conclusion cites file + sheet/cell,
   page or `file:line`. No source → write that it is unconfirmed and must be
   asked. Never present a guess, a typical value or a remembered fact as the
   client's.
4. **Stay in scope.** Do only what was asked. A new approach, a PoC, extra
   rows, renames, deletions, extra sections → propose and wait for a yes.
5. **Feedback ledger.** Keep a numbered list of every correction the user gave
   in this task. Before handing back, go through it and mark each item done
   or not done in the reply.
6. **Check before handoff.** Run `brse-toolkit:review-gate` before every
   handoff: plugin scripts (`office-diff.py`, lint) and an independent second
   agent (`ask-agent.py`) — never a script written on the spot to "prove" the
   work. Office files: render to an image and look at it before saying it's
   done.
7. **Client files.** Never overwrite an original — write a copy in
   <outputs folder>, keep its formatting (fonts, colours, merged cells,
   images, shapes). Prefer the office CLI the config lists over rewriting the
   file with a library. Real client data: no rows created or removed unless
   asked; report exactly which cells changed.
8. **Writing.** Match the deliverable: estimate cells and slide bullets are
   short noun phrases, one idea each, no filler; emails and Q&A answers are
   complete sentences in the client's register. Bilingual sheets: one full
   table per language side by side, never alternating JA/VI columns. Same
   level of detail as the surrounding rows — not finer, not coarser.
9. **Memory.** When the user confirms a term, convention, party or decision,
   write it to `.brse/memory/long/` immediately, with source and date. A
   correction that applies beyond this task → propose adding it to
   `conventions.md`.
10. **Handoff format.** End with: output path(s) · what changed · checks run
    and their result · open questions for the client.
<!-- brse-toolkit:end -->
```

## 6. Git

Check `git rev-parse --is-inside-work-tree`. Not a repo → run `git init`
(`cross-check` uses git history to compare a document with its previous
version).

## 7. Report

Tell the user, in the reply language: what was created, which answers were
left at their defaults, and that `/brse-toolkit:doctor` shows which optional
tools (second agent, machine translation, draw.io) are available. Then offer
to run `/brse-toolkit:ingest` now so the source documents become searchable
(run it only on a yes).
