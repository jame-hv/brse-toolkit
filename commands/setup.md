---
name: setup
description: Install what brse-toolkit needs on this machine — Python packages into a private venv, and, only with the user's yes per item, optional tools (ripgrep, OCR, LibreOffice, draw.io, codex/gemini CLIs, office CLIs)
---

Talk to the user in their language. Install nothing without an explicit yes for
that item. Never put an API key, password or token into any file, and never
change system security settings (sandboxing, AppArmor, firewall, antivirus).

## 1. Python

Try `python3 --version`, `python --version`, `py -3 --version` (in that order).
None works → read `${CLAUDE_PLUGIN_ROOT}/config/dependencies.json`, show the
Python install command for this OS, and ask. After installing, the user may
need to open a new terminal so PATH picks it up — say so, then continue.
Call the working interpreter `<py>`.

## 2. See what's there

Run `<py> ${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py` and show one table: item,
found / missing, what it's for. Then ask, as one multiple-choice question,
which missing items to set up. Pre-select "Python packages" (the only core
item); everything else is optional.

## 3. Python packages (private venv — never the system Python)

Use the `venv.path` / `venv.python` that doctor printed:

1. `<py> -m venv "<venv.path>"`. On Debian/Ubuntu this can fail with
   "ensurepip is not available" → the OS package `python3-venv` is missing;
   show its install command and stop this step.
2. `"<venv.python>" -m pip install -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"`.
3. Record it: in `~/.config/brse-toolkit/config.json` set
   `runtime.python` to `<venv.python>` — merge into the existing file, never
   overwrite other keys. Then run
   `"<venv.python>" ${CLAUDE_PLUGIN_ROOT}/scripts/brse-config.py` and confirm
   there is no `error`.

## 4. Each selected tool

In dependency order (`needs` first, e.g. node before codex):

- Show the exact command from doctor's `install` field and what it changes.
  Commands with `sudo` or that open an admin prompt (winget, brew cask) need the
  user's own password: ask the user to run them themselves by typing
  `! <command>` in the prompt, rather than running them for them.
- After each install, re-check just that item (`doctor.py`) before moving on.
  Failed → show the error, don't retry blindly, move to the next item.

**Items with no standard installer** (doctor shows `manual`, e.g. the office
CLIs): give the download page. If the user already has the app, help locate
its CLI and record the path:
- Linux AppImage: extract only the CLI —
  `"<app>.AppImage" --appimage-extract 'usr/bin/<cli-name>'` run inside
  `<venv.path>/../bin/<cli-name>/` — then check `<that>/squashfs-root/usr/bin/<cli-name> --help` runs.
- Windows / macOS: ask the user for the install folder; the CLI is usually
  next to the app's executable. Check `<path> --help` runs.
- Write the working path to `tools.paths.<id>` in
  `~/.config/brse-toolkit/config.json` (merge, don't overwrite).

**codex / gemini**: after installing, the user signs in themselves
(`codex login`, `gemini`), or sets an API key as an environment variable in
their own shell profile — tell them which variable name the config expects
(`providers.*.api_key_env`). Never ask them to paste a key into the chat.

## 5. Finish

Run `doctor.py` once more with `<venv.python>` and show the final table, plus
what still runs in a reduced mode and why.
