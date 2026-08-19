---
name: init
description: Scaffold documents/, templates/, memory/, CLAUDE.md for a new BrSE project in the current directory
---

Run the following steps in the current directory (the user's project directory, NOT the plugin repo):

1. If `memory/` already exists — stop, ask the user whether to overwrite, do not continue on your own.
2. Create the directories: `documents/`, `templates/`, `memory/`.
3. Create `templates/README.md` with this content:
   "Put the client's own report/slide/DD templates here (font, colors, column structure). The report-gen/detail-design-jp skills read files from this directory when present, and fall back to defaults otherwise."
4. Create 4 files in `memory/`, each with only a title line + schema guidance (empty, no real data yet). Written in English so the scaffolding is readable by any team; actual entries (translations, decisions, etc.) get filled in whatever language the project's deliverables use:

   `memory/parties.md`:
   ```
   # Parties — who is who in this project

   Entry schema:
   - <Party name> — role: <client/vendor/our team/...> — default form of address: <not yet confirmed — use neutral pronouns (e.g. formal "we"/"you") until confirmed>
   ```

   `memory/glossary.md`:
   ```
   # Glossary JP-VI

   Entry schema:
   - <term JP> → "<translation VI>" — source: <file>, <version/date>, confirmed <date>
   ```

   `memory/conventions.md`:
   ```
   # Conventions — ad-hoc formatting conventions

   Entry schema:
   - <format description, e.g. "red text in Excel sheet X"> → <confirmed meaning> — source: <file>, confirmed <date>
   ```

   `memory/decisions-log.md`:
   ```
   # Decisions log — overlay on top of the official DD/spec

   Entry schema:
   - Decision: <content, state the scope of applicability clearly>
     Source: QA #<id>, date <date>
     Status in the official doc: <FULLY updated / PARTIALLY updated / NOT YET updated>
   ```

5. Create `CLAUDE.md` at the project root (if it doesn't exist yet — if it does, append instead of overwriting):

   ```markdown
   ## brse-toolkit memory

   Before running any brse-toolkit skill, read `memory/parties.md`,
   `memory/glossary.md`, `memory/conventions.md`, `memory/decisions-log.md`.

   When new information surfaces (a term, a convention, a relationship between parties,
   a QA decision) — confirm it with the user in one short sentence, then **write it to
   the corresponding file immediately**, before moving on to other work. Don't batch
   confirmations and write them all at the end of the session — the conversation can get
   compacted, the file can't.

   ## brse-toolkit — how to behave toward the end user

   This plugin's users are BrSEs, not developers — they can't read raw tool
   calls/output.

   - Received a passage/file with no clear instruction on what to do with it (e.g. a
     pasted Japanese passage with no accompanying instruction) — **stop and ask first**,
     don't guess: "Translate, cross-check, or something else?". If it's a translation,
     also ask for the target language (default JP→VI, but confirm if unclear). Only
     pick a skill on your own once the intent is clearly stated.
   - Before running a skill, subagent, or script — say one short plain-language sentence
     describing what you're about to do (e.g. "Using the jp-vi-translate skill to
     translate this passage", "Splitting 3 emails into 3 parallel subagents"). Don't
     dump the raw tool call/command in front of the user.
   ```

   (This injected block configures the project's own `CLAUDE.md`, addressed to whoever
   works in that project — keep it in English for the same reason as the memory files
   above, regardless of what language the project's deliverables end up in.)

6. Check whether the current directory is already a git repo (`git rev-parse --is-inside-work-tree`).
   If not, run `git init` — the anti-staleness mechanism in `cross-check` needs git
   history to retrieve prior versions when comparing documents.
7. Report back to the user: done, list the files/directories just created.
