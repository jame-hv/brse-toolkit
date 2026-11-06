You are reviewing the WORDING of a text written for this reader: {reader}
Language of the text: {lang}. You did not write it.

Read every sentence (or every diagram label) as that reader would — someone who
has not read the source documents. List every one that has a problem:
- unclear: the reader cannot tell what it means
- ambiguous: it can be read in more than one way
- translated-feel: word-for-word from another language, not how a native speaker writes
- abbreviation: any short form or initials (forbidden) — write the full name
- wrong-term: a term that differs from the project glossary or the source document's own word
- unnatural: grammatically odd, clumsy, repeated words
- vague: a vague quantity where the reader needs a number
- invented: a name or phrase that looks like the document's wording but is not (renamed terms)

The project's own conventions and glossary below are the standard — a sentence
that breaks one of them is a problem even if it reads fine.

Answer with ONLY this JSON:
{"issues": [{"text": "<the exact sentence or label>", "type": "<one type above>",
  "problem": "<what is wrong, one line>", "rewrite": "<the sentence rewritten correctly>"}]}
An empty list means every sentence is fine.

=== PROJECT CONVENTIONS ===
{conventions}

=== PROJECT GLOSSARY ===
{glossary}

=== TEXT TO REVIEW ===
{text}
