---
name: init
description: Set up a brse-toolkit workspace in the current directory without asking questions — everything is inferred from the folder, the user corrects what is wrong afterwards
---

Run in the current directory (the user's project, NOT the plugin repo).
`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs. None → tell the user to run `/brse-toolkit:setup`.

**Ask nothing.** The command infers the project name, the client-document
folders, template folders, internal / delivered folders and the client
language from the folder. Anything the user already said in their message
(name, folders, languages) is passed as a flag; nothing else is asked.

1. `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py init [--name ...] [--sources a/,b/] [--templates t/] [--client-language ja|vi|en] [--reply-language vi|ja|en]`
   - "already a workspace" → say so in one line and stop, unless the user
     asked to redo it (then add `--force`; memory, knowledge and registers are kept).
2. `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py config` — `workspace_root` is
   this folder, no `error`, no `warnings`.
3. `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py kb-ingest` so the documents are
   searchable from the first task.
4. Reply in the reply language, short:
   - a table of what was inferred (`inferred` in the output: value and where it
     came from) — the user corrects any line by saying it, and you rerun
     `init --force` with that flag;
   - the ingest result: files read, and by name the partial and unreadable ones.
   No list of questions, no "not set yet".
