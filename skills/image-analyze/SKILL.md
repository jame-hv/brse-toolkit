---
name: image-analyze
description: Use this when the user shares a screenshot, hand-drawn diagram, or error image to interpret — OCR handles printed/UI text first, vision only covers what OCR can't (layout, arrows, handwriting).
---

`<py>` = the Python recorded by `/brse-toolkit:setup` (`runtime.python` in
`~/.config/brse-toolkit/config.json`), else the first of `python3`, `python`,
`py -3` that runs. None → tell the user to run `/brse-toolkit:setup`.

## When to use

A screenshot, scanned page, photo of a whiteboard, hand-drawn or exported
diagram, or error image must be read and interpreted — on its own or as the
image part of an Excel / slide / document.

## Steps (spec section 6.4)

1. **Restate** what the image is expected to show and what the user needs
   from it (the text, the flow, a comparison with the spec).
2. **Printed / UI text by OCR first**:
   `<py> ${CLAUDE_PLUGIN_ROOT}/skills/image-analyze/scripts/ocr-pass.py <image> jpn`
   (again with `eng` / `vie` when the image mixes languages). OCR is more
   reliable than vision for text. `tesseract` or a language pack missing
   (`tesseract --list-langs` shows what exists) → tell the user and point to
   `/brse-toolkit:setup`; don't improvise an install. Continue vision-only and
   say the text is not OCR-verified.
3. **Vision only for what OCR can't do**: layout, grouping, arrow direction,
   handwriting, colours, icons. Describe structure (boxes, containers,
   arrows from → to) explicitly.
4. **Small or dense text**: crop or upscale the region first (an image tool
   from `/brse-toolkit:doctor`, or Pillow) rather than guessing a word.
5. **Compare with the written source** when one exists (spec, sheet,
   previous diagram): list where the image and the text disagree.

## Output

- Text found, with OCR confidence where available.
- Structure: components, groupings, arrows (from → to, label).
- Disagreements with the written source, if compared.
- Everything read by vision is labelled "read from an image — not 100%
  certain"; never presented as equal to structured data from other scripts.

## Handoff

Finish with `review-gate` — it runs `verify-output` as its last step.
