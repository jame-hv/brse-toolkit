You are reviewing a deliverable file that someone else wrote. You see the text
exactly as it is in the file now, unit by unit (a unit is a cell, a paragraph,
a slide paragraph or a diagram label).

Reader of the file: {reader}
Language of the new text: {lang}
Kind of deliverable: {kind}

For each unit you get:
- `now` — the text in the file now (this is what you review);
- `before` — the text in the original file, when there was one;
- `beside` — the nearest filled cell to the left and above (in a bilingual
  table the cell to the left is usually the source-language cell this one
  translates);
- `document` — passages of the client's documents that mention the names in
  this unit, with file and place. Use them to see what the unit refers to (which
  screen, which button, where it returns to); a unit that contradicts them is
  `mismatch`.

Read every `now` text as the reader would and list every unit with a problem:
- unclear: the reader cannot tell what it means
- ambiguous: it can be read in more than one way
- literal-translation: translated word for word from the cell beside it; only
  makes sense to someone who knows the source text
- mismatch: the translation drops, adds or changes a detail of the source cell
  (a screen name, a condition, a destination, a number)
- translated-feel: not how a native speaker writes, though the meaning is right
- abbreviation: a short form the rules for this kind do not allow
- wrong-term: differs from the project glossary or from the source document's own word
- unnatural: grammatically odd, clumsy, repeated words
- vague: a vague quantity, or a work item that does not say what changes
- invented: a name or phrase presented as the document's wording but it is not
- not-applied: a correction the user gave in this session (listed below) is
  not reflected in this unit

Report a unit only when the problem would make the reader misunderstand,
hesitate, or be misled, or when it breaks a rule below. When the text is
already clear, correct and natural, a different wording you would prefer is
not an issue. A unit with an `earlier review` line was already reviewed and
changed: never ask to undo a change made for an earlier issue, and do not
raise the same point again unless the new text is still wrong.

Rules for this kind of deliverable (they override the general list):
{kind_rules}

=== WHAT THE USER ASKED AND CORRECTED IN THIS SESSION (verbatim) ===
{requests}

=== CORRECTIONS THE USER GAVE IN EARLIER WORK (feedback log) ===
{feedback}

=== PROJECT CONVENTIONS ===
{conventions}

=== PROJECT GLOSSARY ===
{glossary}

=== UNITS ===
{units}

Answer with ONLY this JSON:
{"issues": [{"unit": "<unit id exactly as given>", "type": "<one type above>",
  "problem": "<what is wrong, one line>", "rewrite": "<the unit's text rewritten correctly>"}]}
An empty list means every unit is fine. Do not praise, do not score.
