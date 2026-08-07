import json
import subprocess
import sys
import pathlib

import openpyxl
from openpyxl.drawing.image import Image as XLImage
from PIL import Image as PILImage

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "extract-images.py"


def make_fixture(xlsx_path, png_path):
    PILImage.new("RGB", (10, 10), color="red").save(png_path)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ScreenA"
    img = XLImage(str(png_path))
    ws.add_image(img, "B10")
    wb.save(xlsx_path)


def run(xlsx_path, out_dir):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(xlsx_path), str(out_dir)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout), result.returncode


def test_extracts_embedded_image_with_anchor(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    png = tmp_path / "src.png"
    out_dir = tmp_path / "out"
    make_fixture(xlsx, png)
    out, code = run(xlsx, out_dir)
    assert code == 0
    assert len(out["images"]) == 1
    entry = out["images"][0]
    assert entry["sheet"] == "ScreenA"
    assert pathlib.Path(entry["file"]).exists()


def test_no_images_returns_empty_list(tmp_path):
    xlsx = tmp_path / "empty.xlsx"
    wb = openpyxl.Workbook()
    wb.save(xlsx)
    out_dir = tmp_path / "out"
    out, code = run(xlsx, out_dir)
    assert out["images"] == []
