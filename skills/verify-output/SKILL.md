---
name: verify-output
description: Mandatory before sending any conclusion — checks every claim has a source, bans vague hedge words. Runs at the end of every other skill in brse-toolkit, never invoked manually.
---

## Policy (spec section 6.1)

1. List out every concluding sentence in the draft response.
2. Every concluding sentence must carry a source tag: `(nguồn: file:dòng)` /
   `(nguồn: sheet, ô)` / `(nguồn: spec trang X)`. These are literal Vietnamese
   tags matched verbatim by the lint script's regex (`lint-hedge-words.py`) —
   do not translate or reformat them, even though the response itself may be
   drafted in Vietnamese for the reader.
3. Can't attach a source → write "chưa xác định được — cần hỏi khách" (not yet
   determined — needs to be asked to the client), never state it as fact.
4. Banned hedge words in conclusions — checked literally by the script, do not
   substitute English equivalents: "có lẽ" (maybe), "chắc là" (probably),
   "hình như" (seems like), "có thể" (might/could). Not banned when the
   sentence is itself a question back to the client.

## Mechanism

Before sending the final answer, run:

    python3 ${CLAUDE_PLUGIN_ROOT}/skills/verify-output/scripts/lint-hedge-words.py <draft.txt>

Read the returned JSON. If `ok: false`, fix the draft until it's clean of
violations before answering — never skip past the script's result.
