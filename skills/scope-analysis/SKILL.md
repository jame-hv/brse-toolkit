---
name: scope-analysis
description: Use this when a set of client documents (RFP, spec, minutes, source code notes) must be turned into a requirement list, a list of gaps / ambiguities / contradictions, and a Q&A sheet to send the client so the scope is clear before estimating or proposing.
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

Documents arrived and the scope must be understood before any estimate,
proposal or design: "analyse these and tell me what to ask the client".
Step 2–4 of `/brse-toolkit:estimate-project`.

## Steps

1. **Intake.** Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/kb-ingest.py`. Show the
   manifest: every file with origin (client / internal / delivered), status,
   and what still needs visual reading. Read the `partial` items visually
   (`excel-analyze` / `image-analyze`) before going on.
2. **Requirement list** `R-001…`: one row per requirement, from **client**
   documents only (`kb-search.py --origin client` to locate, then read the
   part). Columns: ID · category (functional / non-functional / data /
   integration / infrastructure / migration / test / operation / deliverable
   / schedule) · requirement (one sentence, client's wording) · source ref ·
   quantity if stated. Internal documents may add *assumptions*, never
   requirements.
2b. **Explain the current business first** — before any gap or question, write
   for the user (who may know nothing of this domain): who the parties are
   (client, end client, other vendors — one line each), what each system does,
   and the current business flow step by step, with a `diagram` swimlane (one
   lane per person / system). No abbreviations. Every domain term keeps the
   document's own word, with its literal meaning and location — never a name
   you made up. Separate "the document says" (quote + location) from "my
   reading". No invented example data. Keep a term table at the end
   (term as written · literal meaning · where it appears).
2c. **Change table, with numbers** — for each requested change: current
   behaviour → requested behaviour → objects that change, **counted** (screens
   new / changed-major / changed-minor / removed, interfaces, DB tables/columns,
   reports, batches) → what drives the effort → assumptions. Count by comparing
   documents yourself: when an old and a new spec exist, diff them screen by
   screen (`cross-check`) — never write "almost all" or "small", and never ask the
   client for something a comparison of the sources answers.
3. **Gap list** `G-001…`, checked against every category above:
   - ambiguous — two readings are possible (quote both);
   - contradictory — two documents disagree (cite both);
   - missing — the effort depends on it and no document says it
     (quantities, environments, data volume, who does what, test levels,
     acceptance criteria, schedule constraints, support period);
   - implicit — something every vendor would assume; make it explicit.
   Each gap: what is unclear, why it changes the estimate (direction and
   rough size), and the default assumption we would take if unanswered.
   **A gap that does not change the effort is not a question** — it is a design
   detail for later. A gap the sources can close (another document, an older
   spec, the code) is closed by reading them, not by asking.
4. **Gate**: show the requirement list and gap list; the user confirms or edits
   before any question is written.
5. **Q&A sheet**: one question per confirmed gap, in the client's language
   and register (`qa-tone-brse` tone for an Excel Q&A list), in the client's
   Q&A template from `config.paths.templates` (or the project's previous Q&A
   file). Columns at least: No. · category · reference (document + place) ·
   question · our proposal / assumption if no answer · impact on estimate ·
   priority (A = blocks the estimate, B = changes it, C = detail). Group by
   priority A first. Write the file into `config.paths.outputs` via
   `office-text.py` / the office CLI.
6. **Record**: requirement list and gap list saved as internal documents
   (Markdown or xlsx in the first `config.paths.internal` folder);
   `.brse/memory/long/estimate-status.md` updated with the stage
   ("Q&A v1 drafted, waiting for review").

## Output — in this order, for the stated reader

1. Answers to the user's questions, one by one, in the order asked.
2. The current business and systems (text + swimlane diagram).
3. The change table with counts.
4. Questions that change the effort (priority A/B), each with "if X then +N…".
5. Term table (every company, system and domain term used, in full).
Then counts, the lists' paths, the Q&A file path. Before sending, re-read the
reply as the user would — someone who has not read the documents — and fix
every place they would have to ask "what is this?" or "how many?". Then `review-gate`
(`verify-claims.py` on every requirement's source ref).
