import json

import docx
import openpyxl

from brse_testkit import run_script


def claims_file(tmp_path, claims):
    f = tmp_path / "claims.json"
    f.write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
    return f


def test_verify_claims_checks_cells_lines_and_quotes(ws, tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "機能一覧"
    wb.active["D4"] = "初回"
    wb.save(ws / "src-docs" / "req.xlsx")
    d = docx.Document()
    d.add_paragraph("会員登録は第2フェーズで対応する。")
    d.save(ws / "src-docs" / "minutes.docx")
    (ws / "src-docs" / "app.py").write_text("def fee():\n    return price * 1.1\n", encoding="utf-8")
    f = claims_file(tmp_path, [
        {"claim": "D4 says first release", "file": "src-docs/req.xlsx", "locator": {"cell": "機能一覧!D4"}, "expect": "初回"},
        {"claim": "D4 says phase 2", "file": "src-docs/req.xlsx", "locator": {"cell": "機能一覧!D4"}, "expect": "第2フェーズ"},
        {"claim": "tax 1.1", "file": "src-docs/app.py", "locator": {"line": 2}, "expect": "price * 1.1"},
        {"claim": "minutes", "file": "src-docs/minutes.docx", "expect": "会員登録は第2フェーズ"},
        {"claim": "invented quote", "file": "src-docs/minutes.docx", "expect": "決済はクレジットのみ"},
        {"claim": "missing file", "file": "src-docs/nope.xlsx", "expect": "x"},
    ])
    r = run_script("verify-claims.py", f, ws, tmp=tmp_path)
    out = json.loads(r.stdout)
    assert [x["status"] for x in out["results"]] == ["ok", "mismatch", "ok", "ok", "not_found", "file_missing"]
    assert out["results"][1]["actual"] == "初回"
    assert r.returncode == 1


def test_verify_claims_all_ok_exits_zero(ws, tmp_path):
    (ws / "src-docs" / "a.txt").write_text("合計 1105 FP\n", encoding="utf-8")
    f = claims_file(tmp_path, [{"claim": "total", "file": "src-docs/a.txt", "locator": {"line": 1}, "expect": "1105"}])
    assert run_script("verify-claims.py", f, ws, tmp=tmp_path).returncode == 0


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_judge_parse_applies_thresholds(ws, tmp_path):
    good = write(tmp_path, "good.txt", 'ok {"scores": {"correctness": 5, "completeness": 4, "logic": 4, '
                 '"evidence": 4, "language": 4, "scope": 5, "reader": 4}, "must_fix": []}')
    r = run_script("judge.py", "parse", good, "--project", ws, tmp=tmp_path)
    assert r.returncode == 0 and json.loads(r.stdout)["pass"] is True
    weak = write(tmp_path, "weak.txt", '{"scores": {"correctness": 3, "completeness": 4, "logic": 4, '
                 '"evidence": 2, "language": 4, "scope": 5, "reader": 2}, "must_fix": ["D4 cited wrongly"]}')
    out = json.loads(run_script("judge.py", "parse", weak, "--project", ws, tmp=tmp_path).stdout)
    assert out["pass"] is False and out["failed"] == {"correctness": 3, "evidence": 2, "reader": 2}
    assert out["must_fix"] == ["D4 cited wrongly"]


def test_judge_rejects_incomplete_or_non_json_reply(ws, tmp_path):
    partial = write(tmp_path, "p.txt", '{"scores": {"correctness": 5}}')
    assert "no score for" in json.loads(run_script("judge.py", "parse", partial, "--project", ws, tmp=tmp_path).stdout)["error"]
    prose = write(tmp_path, "q.txt", "Looks fine to me!")
    assert json.loads(run_script("judge.py", "parse", prose, "--project", ws, tmp=tmp_path).stdout)["pass"] is False


def test_judge_run_without_second_agent_hands_back_prompt(ws, tmp_path):
    cfg = json.loads((ws / ".brse" / "config.json").read_text(encoding="utf-8"))
    cfg["review"] = {"second_agent": ["codex", "claude-subagent"]}
    (ws / ".brse" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    req, work = write(tmp_path, "req.txt", "translate"), write(tmp_path, "work.txt", "bản dịch")
    r = run_script("judge.py", "run", req, work, "--project", ws, tmp=tmp_path, env={"PATH": str(tmp_path / "empty")})
    out = json.loads(r.stdout)
    prompt = out["next"].split('"')[1]
    assert out["provider"] == "none" and "bản dịch" in open(prompt.split()[1], encoding="utf-8").read()
    # the reviewer's answer comes through the plugin's hook, then the same judge run gives the verdict
    scores = {c: 5 for c in ["correctness", "completeness", "logic", "evidence", "language", "scope", "reader"]}
    hook = {"cwd": str(ws), "tool_name": "Agent",
            "tool_input": {"subagent_type": "brse-toolkit:reviewer", "prompt": prompt},
            "tool_response": {"handbackReport": {"text": json.dumps({"scores": scores, "must_fix": []})}}}
    run_script("hook", "agent-done", stdin=json.dumps(hook), tmp=tmp_path)
    r = run_script("judge.py", "run", req, work, "--project", ws, tmp=tmp_path, env={"PATH": str(tmp_path / "empty")})
    out = json.loads(r.stdout)
    assert r.returncode == 0 and out["pass"] and out["provider"].startswith("claude-subagent")


def test_lang_lint_catches_untranslated_and_style_mix(tmp_path):
    vi = write(tmp_path, "vi.txt", "Bản phát hành đầu tiên chỉ gồm tìm kiếm. Hội viên sẽ làm ở 第2フェーズ. Mã `E0025` giữ nguyên.")
    r = run_script("lang-lint.py", vi, "--lang", "vi", "--source-lang", "ja")
    out = json.loads(r.stdout)
    assert r.returncode == 1 and [f["text"] for f in out["findings"] if f["rule"] == "untranslated"] == ["第", "フェーズ"]
    ja = write(tmp_path, "ja.txt", "本書は設計を示します。検索機能は必須である。ﾃｽﾄを実施します。")
    out = json.loads(run_script("lang-lint.py", ja, "--lang", "ja").stdout)
    rules = {f["rule"] for f in out["findings"]}
    assert {"halfwidth-kana", "ja-style-mix"} <= rules


def test_lang_lint_clean_text_passes(tmp_path):
    ja = write(tmp_path, "ok.txt", "本書は検索機能の設計を示します。初回リリースの対象です。")
    r = run_script("lang-lint.py", ja, "--lang", "ja")
    assert r.returncode == 0 and json.loads(r.stdout)["findings"] == []

