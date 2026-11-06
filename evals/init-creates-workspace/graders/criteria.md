---
type: llm
weight: 1
---

Pass only if ALL of these hold, judged from the tool calls and the final reply:

1. `.brse/config.json` was created, is valid JSON, and records project name
   `sample-shop`, client language Japanese, team and reply language
   Vietnamese, sources `input/`, and the two deliverables.
2. The config contains no API key, token or other secret value.
3. `.brse/memory/long/` contains parties, glossary, conventions and
   decisions-log files holding only a title and schema — no invented terms,
   parties or decisions.
4. `.brse/memory/short/` and `.brse/knowledge/` exist (ingest ran), `config.json` has `"layout_version": 2`, `config.local.json` holds the reply language, `memory/long/` also has `feedback-log.md` and `deliverables-log.md`, and `.brse/.gitignore`
   ignores `memory/short/`, `knowledge/` and `config.local.json`.
5. `CLAUDE.md` contains a block between `<!-- brse-toolkit:start -->` and
   `<!-- brse-toolkit:end -->` that mentions sample-shop and `input/`.
6. The agent re-ran `brse-config.py` (or equivalent) after creating the files
   to confirm the workspace loads without errors or warnings.
7. The final reply is in Vietnamese and states what was created.
