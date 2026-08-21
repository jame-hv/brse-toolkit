---
name: report-gen
description: Use this when the user needs to export a report as Excel, Slide, or Word matching the client's template.
---

## Before running

Check whether `documents/`, `templates/`, `memory/` exist in the current project directory:
- Only one secondary directory missing (`documents/` or `templates/`), `memory/` still present → create the empty directory yourself, use defaults for this run, report it in one clear line. No need to ask.
- `memory/` missing → **do not** silently continue. Stop and ask: "This project hasn't been initialized (`memory/` is missing) — run `/brse-toolkit:init` first so things get saved for next time, or continue once without saving anything?"
- Running as a subagent dispatched by a main agent (spec section 11 batch processing) → the main agent has already resolved this gate before dispatching — do not re-trigger the stop-and-ask, proceed directly. Only apply the check above when invoked directly with no parent agent to have already cleared it.

## Template source

Check `templates/` (project directory — NOT the default template bundled in
`skills/detail-design-jp/templates/`, two different things, see spec section 7)
— if the client has their own template, open it with
`python-pptx`/`python-docx`/`openpyxl` and fill in the content, preserving the
design. None yet → use a simple default template, and state it plainly in the
response: "chưa có template khách, dùng mẫu mặc định — xác nhận format sau."
(the literal note to give the user, in Vietnamese since that's the working
language of the response).

## Concrete flow (spec section 6.9)

1. **Where the content comes from** — never invent it. Status report →
   `memory/decisions-log.md` + `cross-check`/`code-to-business` if available.
   Proposed solutions → chain through `proposal-gen` first. User provides
   content directly → use that content.
2. **Determine the template** — as above.
3. **Determine the audience** — apply the relay model (spec section 2): a
   client-facing (Japanese) version differs from an internal PM/dev version.
   Unclear → ask before drafting; don't silently assume internal just because
   the request didn't specify.
4. **Determine the format and its shape** — Excel, Slide, or Word are not
   interchangeable defaults for "a report":
   - **Slide** (`python-pptx`): a claim/figure that can't be sourced goes in
     the **speaker notes** as "cần xác nhận thêm", never on the slide itself
     as a settled fact.
   - **Excel** (`openpyxl`): naturally fits anything row-shaped — a test
     case/bug tracker, a status report with one row per item — an unsourced
     figure goes in a dedicated remark/note column, not silently into the
     tracked value cell.
   - **Word** (`python-docx`): fits prose-shaped content — a narrative status
     summary, a memo. An unsourced claim goes in a clearly separated "Notes /
     ghi chú nội bộ (không gửi khách)" section at the end of the document, not
     interleaved into the main narrative.
   Ambiguous which shape fits (e.g. "weekly status report" could reasonably be
   either a Word narrative or an Excel tracker) → ask rather than picking
   silently, since the two shapes hold genuinely different content structure,
   not just a different file extension.
5. **Apply `verify-output`** per bullet/row/paragraph per the format's
   unsourced-claim placement above.
6. Generate the actual file with the library matching the format chosen in
   step 4.
7. **Output**: the file + a short list of "assumptions/unconfirmed points" kept
   SEPARATE for the user to review before sending — never mixed into the file
   itself (this is IN ADDITION TO the in-file placement in step 4, not instead
   of it — the chat response should let the user see the open points without
   opening the file).
