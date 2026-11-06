---
name: doctor
description: Show which tools brse-toolkit can use on this machine (Python and its packages, office CLIs, draw.io, OCR, second agents) and what is missing — read-only, installs nothing
---

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs.

1. No Python runs at all → say so, show the Python install command for this
   OS from `${CLAUDE_PLUGIN_ROOT}/config/dependencies.json` (read the file
   directly), suggest `/brse-toolkit:setup`, and stop.
2. Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py` in the current directory.
3. Show the user, in their language, one table: tool, found / missing, what it
   is used for. Below it, for each missing item: the install command (or the
   download page when there is no standard installer). Missing Python packages
   → one line pointing to `/brse-toolkit:setup`.
4. `config_error` not null → show it first; the config must be fixed.
5. Say which features run in a reduced mode because of what is missing (e.g.
   no office CLI → Python libraries are used for .xlsx; no second agent →
   reviews are done by a separate Claude subagent, not an independent model).

Never install, never change any setting here — that is `/brse-toolkit:setup`.
