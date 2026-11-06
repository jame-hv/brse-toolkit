"""Checks on the plugin as a whole, not one script: manifests, skill frontmatter,
every ${CLAUDE_PLUGIN_ROOT}/... path the docs point to, config validity, and
that no shipped file carries a machine path or an email address."""
import json
import os
import re
import shutil
import subprocess
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", ".claude", "test-document", "results", "node_modules"}
TEXT_EXT = {".md", ".py", ".json", ".yaml", ".yml", ".ini", ".txt"}


def shipped_text_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in TEXT_EXT and not SKIP_DIRS & set(p.relative_to(ROOT).parts):
            yield p


def frontmatter(md: pathlib.Path) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", md.read_text(encoding="utf-8"), re.S)
    assert m, f"{md} has no frontmatter"
    return dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)


def test_manifests_are_valid_json():
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["name"] and plugin["version"] and plugin["description"]
    json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("skill", sorted(p.parent.name for p in ROOT.glob("skills/*/SKILL.md")))
def test_skill_frontmatter_matches_folder(skill):
    fm = frontmatter(ROOT / "skills" / skill / "SKILL.md")
    assert fm["name"].strip() == skill
    assert len(fm["description"].strip()) > 40


def test_every_referenced_plugin_path_exists():
    ref = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)")
    missing = []
    for md in list(ROOT.glob("skills/*/SKILL.md")) + list(ROOT.glob("commands/*.md")):
        for rel in ref.findall(md.read_text(encoding="utf-8")):
            rel = rel.rstrip(".")
            if not (ROOT / rel).exists():
                missing.append(f"{md.relative_to(ROOT)} -> {rel}")
    assert missing == []


def test_config_files_are_valid_and_defaults_load_clean(tmp_path):
    for f in ROOT.glob("config/*.json"):
        json.loads(f.read_text(encoding="utf-8"))
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path / "home")}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "brse-config.py"), str(tmp_path)],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    out = json.loads(r.stdout)
    assert r.returncode == 0 and out["warnings"] == []


def test_no_machine_paths_or_emails_in_shipped_files():
    bad = re.compile(r"/home/[a-z]|/Users/[A-Za-z]|C:\\\\Users|[\w.+-]+@[\w-]+\.(com|net|org|vn|jp)\b")
    hits = [f"{p.relative_to(ROOT)}: {m.group(0)}"
            for p in shipped_text_files() if p.name != "test_plugin_structure.py"
            for m in [bad.search(p.read_text(encoding="utf-8", errors="ignore"))] if m]
    assert hits == []


@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed")
def test_claude_plugin_validate_passes():
    r = subprocess.run(["claude", "plugin", "validate", str(ROOT)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:]
