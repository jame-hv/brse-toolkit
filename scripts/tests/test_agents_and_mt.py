import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from conftest import run_script

posix_only = pytest.mark.skipif(os.name == "nt", reason="fake CLI is a shell script")


def set_config(ws, extra):
    cfg = ws / ".brse" / "config.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data.update(extra)
    cfg.write_text(json.dumps(data), encoding="utf-8")


@posix_only
def test_ask_agent_uses_codex_read_only_and_returns_last_message(ws, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "codex"
    # records its argv, answers with the prompt it got on stdin, via -o <file>
    fake.write_text(f"""#!{sys.executable}
import sys, pathlib
args = sys.argv[1:]
pathlib.Path({str(tmp_path / 'argv.txt')!r}).write_text(" ".join(args))
out = args[args.index("-o") + 1]
pathlib.Path(out).write_text("REVIEW OF: " + sys.stdin.read())
""")
    fake.chmod(0o755)
    set_config(ws, {"review": {"second_agent": ["codex", "claude-subagent"]}})
    prompt = tmp_path / "p.txt"
    prompt.write_text("check this translation", encoding="utf-8")
    r = run_script("ask-agent.py", prompt, ws, tmp=tmp_path, env={"PATH": str(bin_dir)})
    out = json.loads(r.stdout)
    assert out["provider"] == "codex" and out["output"] == "REVIEW OF: check this translation"
    assert "-s read-only" in (tmp_path / "argv.txt").read_text()


def test_ask_agent_reports_none_with_reasons_when_nothing_available(ws, tmp_path):
    set_config(ws, {"review": {"second_agent": ["codex", "gemini", "openai", "claude-subagent"]}})
    prompt = tmp_path / "p.txt"
    prompt.write_text("x", encoding="utf-8")
    env = {"PATH": str(tmp_path / "empty"), "OPENAI_API_KEY": ""}
    out = json.loads(run_script("ask-agent.py", prompt, ws, tmp=tmp_path, env=env).stdout)
    assert out["provider"] == "none"
    assert [t["provider"] for t in out["tried"]] == ["codex", "gemini", "openai", "claude-subagent"]


class FakeDeepL(BaseHTTPRequestHandler):
    seen = {}

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeDeepL.seen = {"auth": self.headers["Authorization"], "body": body}
        data = json.dumps({"translations": [{"text": "Xác nhận đơn hàng"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_mt_uses_deepl_with_key_from_env(ws, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), FakeDeepL)
    threading.Thread(target=server.handle_request, daemon=True).start()
    text = tmp_path / "t.txt"
    text.write_text("注文確認", encoding="utf-8")
    env = {"DEEPL_API_KEY": "k-123", "BRSE_DEEPL_URL": f"http://127.0.0.1:{server.server_port}/"}
    out = json.loads(run_script("mt.py", text, "--to", "vi", "--from", "ja", ws, tmp=tmp_path, env=env).stdout)
    server.server_close()
    assert out["engine"] == "deepl" and out["translation"] == "Xác nhận đơn hàng"
    assert FakeDeepL.seen["auth"] == "DeepL-Auth-Key k-123"
    assert FakeDeepL.seen["body"]["target_lang"] == "VI" and FakeDeepL.seen["body"]["source_lang"] == "JA"


def test_mt_without_any_engine_says_claude_alone(ws, tmp_path):
    text = tmp_path / "t.txt"
    text.write_text("x", encoding="utf-8")
    env = {"DEEPL_API_KEY": "", "OPENAI_API_KEY": ""}
    out = json.loads(run_script("mt.py", text, "--to", "ja", ws, tmp=tmp_path, env=env).stdout)
    assert out["engine"] == "none"
    assert out["tried"][-1]["engine"] == "claude"


def test_mt_rejects_unknown_language(ws, tmp_path):
    text = tmp_path / "t.txt"
    text.write_text("x", encoding="utf-8")
    assert run_script("mt.py", text, "--to", "fr", ws, tmp=tmp_path).returncode == 2


def test_mt_reads_key_from_secrets_file_and_plugin_option(ws, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), FakeDeepL)
    threading.Thread(target=server.handle_request, daemon=True).start()
    secrets = tmp_path / "cfg" / "brse-toolkit" / "secrets.env"
    secrets.parent.mkdir(parents=True)
    secrets.write_text("DEEPL_API_KEY=from-file\n", encoding="utf-8")
    text = tmp_path / "t.txt"
    text.write_text("確認", encoding="utf-8")
    env = {"DEEPL_API_KEY": "", "BRSE_DEEPL_URL": f"http://127.0.0.1:{server.server_port}/"}
    out = json.loads(run_script("mt.py", text, "--to", "vi", ws, tmp=tmp_path, env=env).stdout)
    server.server_close()
    assert out["engine"] == "deepl" and FakeDeepL.seen["auth"] == "DeepL-Auth-Key from-file"

    server = HTTPServer(("127.0.0.1", 0), FakeDeepL)
    threading.Thread(target=server.handle_request, daemon=True).start()
    env.update({"CLAUDE_PLUGIN_OPTION_DEEPL_API_KEY": "from-keychain",
                "BRSE_DEEPL_URL": f"http://127.0.0.1:{server.server_port}/"})
    run_script("mt.py", text, "--to", "vi", ws, tmp=tmp_path, env=env)
    server.server_close()
    assert FakeDeepL.seen["auth"] == "DeepL-Auth-Key from-keychain"  # plugin option beats the file
