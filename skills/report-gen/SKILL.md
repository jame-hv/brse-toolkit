---
name: report-gen
description: Use this when the user needs to export a report as Excel, Slide, or Word matching the client's template.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"

## Template source

Check `templates/` (project directory — NOT the default template bundled in
`skills/detail-design-jp/templates/`, two different things, see spec section 7)
— if the client has their own template, open it with
`python-pptx`/`python-docx`/`openpyxl` and fill in the content, preserving the
design. None yet → use a simple default template, and state it plainly in the
response: "chưa có template khách, dùng mẫu mặc định — xác nhận format sau."
(the literal note to give the user, in Vietnamese since that's the working
language of the response).

## Concrete flow — generating a slide (spec section 6.9)

1. **Where the content comes from** — never invent it. Status report →
   `memory/decisions-log.md` + `cross-check`/`code-to-business` if available.
   Proposed solutions → chain through `proposal-gen` first. User provides
   content directly → use that content.
2. **Determine the template** — as above.
3. **Determine the audience** — apply the relay model (spec section 2): a slide
   for the Japanese client differs from an internal PM/dev slide. Unclear →
   ask before drafting.
4. **Apply `verify-output` per bullet** — a claim/figure that can't be sourced
   → put it in the speaker notes as "cần xác nhận thêm" (needs further
   confirmation), do NOT put it on the slide itself as a settled fact.
5. Generate the actual file with `python-pptx` (or `openpyxl`/`python-docx` for
   Excel/Word).
6. **Output**: the file + a short list of "assumptions/unconfirmed points" kept
   SEPARATE for the user to review before sending — never mixed into the file
   itself.
