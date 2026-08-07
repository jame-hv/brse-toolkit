import json
import shutil
import subprocess
import sys
import pathlib

import openpyxl
import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "render-sheet.py"

pytestmark = pytest.mark.skipif(shutil.which("libreoffice") is None, reason="libreoffice not installed")


def test_render_produces_png_file(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    wb = openpyxl.Workbook()
    wb.active["A1"] = "shape/annotation placeholder"
    wb.save(xlsx)
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(xlsx), str(out_dir)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0
    produced = json.loads(result.stdout)["file"]
    assert produced.endswith(".png")
    assert pathlib.Path(produced).exists()
