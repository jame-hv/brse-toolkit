#!/usr/bin/env python3
"""OCR pass for printed/typed text in an image — more reliable than vision transcription
for text tesseract can read; vision still handles layout/arrows/handwriting.

Usage: ocr-pass.py <image_path> [lang]   (default lang: jpn)
"""
import json
import sys

import pytesseract
from PIL import Image


def ocr(path: str, lang: str = "jpn") -> list[dict]:
    img = Image.open(path)
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    words = []
    for i, text in enumerate(data["text"]):
        if text.strip():
            words.append({
                "text": text,
                "confidence": int(data["conf"][i]),
                "left": int(data["left"][i]),
                "top": int(data["top"][i]),
            })
    return words


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print("usage: ocr-pass.py <image_path> [lang]", file=sys.stderr)
        sys.exit(2)
    lang = sys.argv[2] if len(sys.argv) == 3 else "jpn"
    print(json.dumps({"words": ocr(sys.argv[1], lang)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
