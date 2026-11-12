import json
import os
import pathlib
import shutil

import openpyxl
import pytest

from brse_testkit import run_cli

pytestmark = pytest.mark.skipif(os.name == "nt" or not (shutil.which("soffice") or shutil.which("libreoffice")),
                                reason="LibreOffice not installed")


def test_office_render_xlsx_without_pdftoppm(tmp_path):
    xlsx = tmp_path / "fixture.xlsx"
    wb = openpyxl.Workbook()
    wb.active["A1"] = "shape/annotation placeholder"
    wb.save(xlsx)
    bin_dir = tmp_path / "bin"  # every program on PATH except pdftoppm
    bin_dir.mkdir()
    for d in os.environ["PATH"].split(os.pathsep):
        for exe in pathlib.Path(d).glob("*") if pathlib.Path(d).is_dir() else []:
            link = bin_dir / exe.name
            if exe.name != "pdftoppm" and not link.exists():
                link.symlink_to(exe)
    r = run_cli("office", "render", xlsx, tmp_path / "out", env={"PATH": str(bin_dir)})
    assert r.returncode == 0, r.stdout + r.stderr
    images = json.loads(r.stdout)["images"]
    assert images and all(pathlib.Path(i).suffix == ".png" and pathlib.Path(i).exists() for i in images)
