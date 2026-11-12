---
name: verify-output
description: Mandatory before sending any conclusion — checks every claim has a source, bans vague hedge words. Runs at the end of every other skill in brse-toolkit, never invoked manually.
---

## Policy (spec section 6.1)

1. List out every concluding sentence in the draft response.
2. Every concluding sentence must cite where it comes from, in one of two
   forms:
   - the workspace's source tag, `config.style.source_tag` from
     `brse.py config` (default `(nguồn: {ref})`), with a real ref inside:
     a file + line, a sheet + cell, a spec page, or a chat message + date for
     a requirement that only ever existed as a live message;
   - an inline reference the reader can open directly: `path/file.ext:123`
     or `Sheet!A12`. A bare cell address ("D52") is not enough — say which
     sheet/file.
   The script only checks that a citation-shaped string is present, not that
   it is genuine — picking a real, honest ref is on the author.
3. Can't attach a source → say plainly, in the reply language, that it is not
   yet determined and needs to be asked to the client — never state it as fact.
4. Banned hedge words in conclusions (checked literally by the script; the
   current list is Vietnamese: "có lẽ", "chắc là", "hình như", "có thể"). Not
   banned when the sentence is itself a question back to the client. For
   JP/EN deliverables the same rule applies (no 〜かもしれない / "maybe" in a
   conclusion) even though the script doesn't check those words yet.
5. The script splits Japanese sentences on 。！？ and treats "？" as a
   question mark, so JP deliverables are checked sentence by sentence.

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs. None → tell the user to run `/brse-toolkit:setup`.

## Mechanism

Before sending the final answer, run:

    <py> ${CLAUDE_PLUGIN_ROOT}/scripts/brse.py lint-hedge-words <draft.txt> --source-tag "<config.style.source_tag>"

Read the returned JSON. If `ok: false`, fix the draft until it's clean of
violations before answering — never skip past the script's result.
