import json

from brse_testkit import run_script


def call(tool, **inp):
    return run_script("guard-secrets.py", stdin=json.dumps({"tool_name": tool, "tool_input": inp})).returncode


def test_blocks_direct_access_to_key_files():
    assert call("Read", file_path="/p/.brse/config.local.json") == 2
    assert call("Bash", command="cat .brse/config.local.json") == 2
    assert call("Bash", command="cat ~/.config/brse-toolkit/secrets.env") == 2
    assert call("Grep", pattern="sk-", path="/x/.config/brse-toolkit/secrets.env") == 2


def test_allows_masked_reader_and_normal_work():
    assert call("Bash", command="python3 scripts/brse.py config .  # reads config.local.json masked") == 0
    assert call("Read", file_path="/p/.brse/config.json") == 0
    assert call("Bash", command="ls -la") == 0


def test_garbage_input_never_blocks():
    assert run_script("guard-secrets.py", stdin="not json").returncode == 0
