---
name: ingest
description: Convert the workspace's client source documents (xlsx, docx, pptx, pdf, text) into searchable Markdown under .brse/knowledge and report exactly what could not be read as text
---

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs.

1. Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/kb-ingest.py` (add `--force` only if
   the user asks to rebuild everything). Missing Python packages → point to
   `/brse-toolkit:setup` and stop.
2. Show the user, in their language: how many files, how many converted now,
   and a table of every file that is `partial` (images, charts, pictures that
   need visual reading — name them) or `unreadable` (with the reason).
3. For `partial` items, offer to read them now with `excel-analyze` /
   `image-analyze`; never present the Markdown copy as the complete content of
   such a file.
4. Remind: search with
   `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/kb-search.py "<query>"` — it only finds
   candidates; conclusions come from reading the whole part.
