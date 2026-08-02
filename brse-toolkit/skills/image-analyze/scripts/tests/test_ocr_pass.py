import json
import shutil
import subprocess
import sys
import pathlib

import pytest
from PIL import Image, ImageDraw

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "ocr-pass.py"


def _tesseract_has_lang(lang: str) -> bool:
    if shutil.which("tesseract") is None:
        return False
    result = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    return lang in result.stdout


pytestmark = pytest.mark.skipif(not _tesseract_has_lang("eng"), reason="tesseract with eng traineddata not installed")


def make_fixture(path):
    img = Image.new("RGB", (200, 60), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 15), "HELLO", fill="black")
    img.save(path)


def run(image_path, lang="eng"):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(image_path), lang],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_ocr_extracts_text_with_position(tmp_path):
    img_path = tmp_path / "fixture.png"
    make_fixture(img_path)
    out, code = run(img_path)
    assert code == 0
    texts = [w["text"] for w in out["words"]]
    assert any("HELLO" in t.upper() for t in texts)
    assert all("left" in w and "top" in w and "confidence" in w for w in out["words"])
