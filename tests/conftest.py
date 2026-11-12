import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brse_testkit import make_ws  # noqa: E402


@pytest.fixture
def ws(tmp_path):
    return make_ws(tmp_path)


@pytest.fixture(autouse=True)
def private_data_dir(tmp_path, monkeypatch):
    """Commands run by the tests never write into the developer's real per-user data folder
    (they once filled ~/.local/share/brse-toolkit/checks.json and blocked real sessions)."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "xdg-data"))
