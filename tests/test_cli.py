import json
import subprocess
import sys

from brse_testkit import ROOT, run_cli

THIRD_PARTY = ["openpyxl", "docx", "pptx", "PIL", "pytesseract", "lxml"]


def test_unknown_command_exits_2():
    r = run_cli("khong-co")
    assert r.returncode == 2
    assert "error" in json.loads(r.stdout)


def test_config_from_subfolder(ws, tmp_path):
    (ws / "a" / "b").mkdir(parents=True)
    r = run_cli("config", cwd=ws / "a" / "b", tmp=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["workspace_root"] == str(ws)


def run_without_third_party(command, cwd):
    code = (f"import sys; sys.path.insert(0, {str(ROOT)!r})\n"
            + "".join(f"sys.modules[{m!r}] = None\n" for m in THIRD_PARTY)
            + f"from brse.cli import main; sys.exit(main([{command!r}]))")
    return subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True,
                          encoding="utf-8", cwd=cwd)


def test_config_runs_without_third_party_packages(tmp_path):
    r = run_without_third_party("config", tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_doctor_runs_without_third_party_packages(tmp_path):
    r = run_without_third_party("doctor", tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    packages = {p["package"]: p["found"] for p in json.loads(r.stdout)["python_packages"]}
    assert packages["openpyxl"] is False
