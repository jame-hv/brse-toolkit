---
name: library
description: Save an approved deliverable (estimate, preconditions, proposal, test spec...) to the personal library reused across projects, or list / remove library items
---

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs.

- **Save**: confirm with the user which file, its kind (estimate,
  preconditions, proposal, test-spec, detail-design, report, or their own
  word), a one-line note on what makes it a good reference, and that it was
  approved. Then run
  `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py library add "<file>" --kind <kind> --note "<note>" --project "<project name>"`.
  Remind the user that the library is shared across their projects: a file
  holding one client's confidential data should be saved only if they accept
  that, or after they remove the confidential parts.
- **List**: `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py library list [--kind <kind>]`
  and show a table: id, kind, file name, note, project, date.
- **Remove**: confirm the id with the user, then
  `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py library remove <id>`.

Skills such as `estimation` and `proposal-gen` look here for a reference of
the same kind before starting from scratch, and ask before reusing an item
that came from a different client.
