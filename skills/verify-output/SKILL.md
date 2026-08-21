---
name: verify-output
description: Mandatory before sending any conclusion — checks every claim has a source, bans vague hedge words. Runs at the end of every other skill in brse-toolkit, never invoked manually.
---

## Policy (spec section 6.1)

1. List out every concluding sentence in the draft response.
2. Every concluding sentence must carry a source tag: `(nguồn: file:dòng)` /
   `(nguồn: sheet, ô)` / `(nguồn: spec trang X)` / `(nguồn: chat khách, <ngày>)`
   for a requirement that only ever existed as a live chat message, never a
   file. These are literal Vietnamese tags — do not translate or reformat
   them, even though the response itself may be drafted in Vietnamese for the
   reader. The lint script's regex only checks that a `(nguồn: ...)` wrapper
   is present at all, not that its contents match one of these formats — the
   discipline of picking a real, honest tag is on the author, the script
   cannot verify a citation is genuine, only that a citation-shaped string
   exists.
3. Can't attach a source → write "chưa xác định được — cần hỏi khách" (not yet
   determined — needs to be asked to the client), never state it as fact.
   This exact phrase is not itself checked by the script — the script only
   detects the absence of any source tag, not whether this specific fallback
   wording was used once a source turned out to be missing.
4. Banned hedge words in conclusions — checked literally by the script, do not
   substitute English equivalents: "có lẽ" (maybe), "chắc là" (probably),
   "hình như" (seems like), "có thể" (might/could). Not banned when the
   sentence is itself a question back to the client.
5. Deliverable content itself is Japanese (a DD document, a JP-target
   translation) rather than the Vietnamese chat response — the script
   recognizes Japanese sentence boundaries (。！？, no required trailing
   space) and treats "？" as a question mark the same way as "?", but
   `HEDGE_WORDS` and `SOURCE_TAG_RE` still only match the literal Vietnamese
   strings above — a JP or EN sentence needs the literal `(nguồn: ...)` tag
   embedded in it same as a VI one, there is no JP/EN equivalent tag the
   script recognizes.

## Mechanism

Before sending the final answer, run:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py <draft.txt>

Read the returned JSON. If `ok: false`, fix the draft until it's clean of
violations before answering — never skip past the script's result.
