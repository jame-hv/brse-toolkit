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
   detail design, test spec, Q&A list).

Don't guess answers the user didn't give — leave the default and say so.

## 4. Create the workspace

```
.brse/
├── config.json
├── .gitignore            # contents: "memory/short/" and "knowledge/index.sqlite"
├── memory/
│   ├── long/             # parties.md, glossary.md, conventions.md, decisions-log.md
│   └── short/            # session logs written by the plugin's hooks
└── knowledge/
    └── docs/             # source documents converted to Markdown
```

`.brse/config.json` holds only what the user answered (everything else is
inherited from the plugin defaults and the user's own config):

```json
{
  "project": {
    "name": "<answer 1>",
    "client_language": "<answer 2>",
    "team_language": "<answer 2>",
    "reply_language": "<answer 2>",
    "deliverables": ["<answer 5>"]
  },
  "paths": {
    "sources": ["<answer 3>"],
    "templates": ["<answer 4>"]
  }
}
```

Never write an API key or any other secret into this file — providers are
configured by environment-variable name only (see the README).

The four `memory/long/` files start empty except for their title and schema
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

An entry that gets replaced is never deleted: set its `status` to
`superseded by <date>` and add the new entry below it.

Then run `brse-config.py` again: `workspace_root` must be the current
directory, with no `error` and no `warnings`. Fix the config before going on
if not.

## 5. Write the project CLAUDE.md

Write the block below between the markers `<!-- brse-toolkit:start -->` and
`<!-- brse-toolkit:end -->`. If `CLAUDE.md` exists, replace only an existing
block between those markers (or append the block when there is none) — never
touch the user's own content outside it. Fill every `<...>` from the answers;
write the block in the reply language.

```markdown
<!-- brse-toolkit:start -->
## Project
<project name> — deliverables: <deliverables>.
Client documents are in <client language>; the team works in <team language>;
reply to the user in <reply language>.

## Where things are
- Client sources: <source folders> (converted copies: `.brse/knowledge/docs/`)
- Client templates: <template folders>
- Settled facts: `.brse/memory/long/` (parties, glossary, conventions, decisions)
- Recent sessions: `.brse/memory/short/`
- Settings: `.brse/config.json` (check with `/brse-toolkit:doctor`)

## How to work here
1. Before any non-trivial task, restate in one or two lines what will be
   delivered, in which format, and what is out of scope. Unclear → ask first.
2. Read the sources before concluding — the whole relevant document, not a
   keyword search. Say which sources were read and which were not.
3. Every conclusion cites its source. No source → say it is unconfirmed.
4. Do only what was asked. Anything extra (a new approach, a PoC, a rename,
   a deletion) → propose it and wait for a yes.
5. Before handing work back, check it against the request and against every
   piece of feedback given so far in this task.
6. Never overwrite a client's original file — write to a copy.
7. When the user confirms a term, convention, party, or decision, write it to
   `.brse/memory/long/` right away, with its source and date.
<!-- brse-toolkit:end -->
```

## 6. Git

Check `git rev-parse --is-inside-work-tree`. Not a repo → run `git init`
(`cross-check` uses git history to compare a document with its previous
version).

## 7. Report

Tell the user, in the reply language: what was created, which answers were
left at their defaults, and that `/brse-toolkit:doctor` shows which optional
tools (second agent, machine translation, draw.io) are available.
