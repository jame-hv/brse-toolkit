---
name: brainstorm-brse
description: Use this when the user needs solution/business options for a specific problem (e.g. "what are our options for X", "how should we handle Y with the client") — proposes 2-3 structured options with trade-offs, not open-ended code brainstorming.
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

The user needs options for one concrete business, process or delivery
problem ("which way should we handle X", "how do we explain Y to the
client"). Not this skill: open-ended software design, or a pure fact question
(→ `research-jp-tech`).

## Steps

1. **Restate** the problem in one line, plus the constraints that decide the
   answer: deadline, budget/effort ceiling, who decides, what the client has
   already agreed (check `.brse/memory/long/decisions-log.md`). A missing
   constraint that would change the recommendation → ask one question first.
2. **Collect facts** from the sources and memory. A fact the options depend on
   but nobody has verified (version compatibility, tool capability, contract
   term) → verify it (`research-jp-tech`, or a minimal check that is actually
   run) or list it under *Unverified*. Never write "works on X" or "is
   supported" from memory.
3. **Build 2–3 options that differ in substance** — not three flavours of one
   idea. For each: what we would do, what we gain, what we give up (effort,
   time, risk), what the client must do or accept, and how it would be
   explained to them in one sentence.
4. **Recommend one**, with the deciding reason tied to the constraints from
   step 1.
5. Stop there. No implementation, no PoC, no file changes unless the user
   picks an option and asks for it.

## Output

| Option | What we do | Gain | Give up | Client impact | Risk |
|---|---|---|---|---|---|

**Recommendation:** <option> — <reason tied to a constraint>.
**Unverified:** <facts the options rely on that still need checking>.
**Needed from the user / client:** <decisions or inputs>.

Keep it under ~25 lines unless the user asks for depth.

## Checks before answering

- Every cell in the table that states a fact has a source, or the fact is in
  *Unverified*.
- The options are genuinely different (a reader could choose between them).
- Run `verify-output`.
