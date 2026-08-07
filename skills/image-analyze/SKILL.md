---
name: image-analyze
description: Read screenshots/hand-drawn diagrams/error images — OCR first for printed/UI text, vision only handles layout/arrows/handwriting.
---

## Mechanism (spec section 6.4)

1. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/image-analyze/scripts/ocr-pass.py <image> jpn` —
   printed/UI text, more reliable than letting vision read it itself. If the
   image has English/Vietnamese text, call again with `lang=eng`/`vie`.
2. Vision only handles what OCR can't: layout, arrow direction, handwriting.
3. Always attach a clear confidence value (use the `confidence` field from OCR
   when available), and do NOT present it as equally reliable as structured
   data from other scripts (e.g. `extract-cells.py`).

## Output

A structured description (UI components, arrow flow, text in the image) to
cross-check against the written spec — flag it as questionable if the image
doesn't match the spec, per `verify-output`.
