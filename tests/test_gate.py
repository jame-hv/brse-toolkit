"""The final check runs on the file itself, needs every issue answered, and the Stop hook enforces it."""
import json
import os
import time

import openpyxl

from brse_testkit import run_cli


def setup(ws, tmp_path):
    cfg = json.loads((ws / ".brse" / "config.json").read_text())
    cfg["review"] = {"second_agent": ["claude-subagent"]}  # no second model: the reviewer is the subagent
    (ws / ".brse" / "config.json").write_text(json.dumps(cfg))
    (ws / "output").mkdir()
    t = tmp_path / "t.jsonl"
    t.write_text(json.dumps({"type": "user", "timestamp": "2000-01-01T00:00:00Z",
                             "message": {"role": "user", "content": "làm sheet song ngữ"}}) + "\n")
    run_cli("hook", "session-start", stdin=json.dumps({"cwd": str(ws), "session_id": "s1",
                                                        "transcript_path": str(t)}), tmp=tmp_path)
    return t


def book(path, vi="Hỗ trợ màn A"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "明細"
    ws["A1"], ws["B1"] = "作業項目", "Hạng mục"
    ws["A2"], ws["B2"] = "画面Aの戻る先を画面Bに変更", vi
    wb.save(path)


def gate(ws, tmp_path, *args):
    r = run_cli("gate", *args, tmp=tmp_path, cwd=ws)
    return r.returncode, json.loads(r.stdout)


def answer(ws, tmp_path, next_text, issues):
    prompt = next_text.split('"')[1]  # "BRSE-GATE <prompt file>"
    hook = {"cwd": str(ws), "tool_name": "Agent",
            "tool_input": {"subagent_type": "brse-toolkit:wording-reviewer", "prompt": prompt},
            "tool_response": {"content": [{"type": "text", "text": json.dumps({"issues": issues})}]}}
    run_cli("hook", "agent-done", stdin=json.dumps(hook), tmp=tmp_path)


def stop(ws, t, tmp_path):
    r = run_cli("hook", "stop", stdin=json.dumps({"cwd": str(ws), "session_id": "s1", "transcript_path": str(t)}),
                tmp=tmp_path)
    return json.loads(r.stdout) if r.stdout.strip() else None


def test_gate_reviews_the_file_needs_answers_and_stamps(ws, tmp_path):
    t = setup(ws, tmp_path)
    f = ws / "output" / "est.xlsx"
    book(f)

    code, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    assert code == 1 and "BRSE-GATE" in out["next"]
    prompt = next((ws / ".brse" / "gate").glob("*.prompt.md")).read_text()
    assert "now: Hỗ trợ màn A" in prompt and "画面Aの戻る先を画面Bに変更" in prompt  # the cell beside it
    assert "làm sheet song ngữ" in prompt  # the user's own words from this session
    assert "「〜への対応」" in prompt  # rules for estimate cells

    answer(ws, tmp_path, out["next"], [{"unit": "明細!B2", "type": "vague", "problem": "không nói đổi gì",
                                        "rewrite": "Đổi màn quay về của màn A thành màn B"}])
    code, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    assert code == 1 and out["open_issues"][0]["id"] == "I1"

    # claiming "fixed" without changing the cell does not work
    gate(ws, tmp_path, "resolve", f, "I1", "fixed")
    code, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    assert code == 1 and "did not change" in out["open_issues"][0]["note"]

    # change the cell → it is reviewed again → clean → stamped
    book(f, "Đổi màn quay về của màn A thành màn B")
    gate(ws, tmp_path, "resolve", f, "I1", "fixed")
    code, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    assert code == 1 and "BRSE-GATE" in out["next"]
    answer(ws, tmp_path, out["next"], [])
    code, out = gate(ws, tmp_path, "check", f, "--kind", "estimate-cell")
    assert code == 0 and out["pass"] and "1 issue(s) fixed" in out["summary"]
    assert stop(ws, t, tmp_path) is None

    # editing after the stamp voids it, and the Stop hook refuses
    time.sleep(0.01)
    book(f, "Đổi màn quay về của màn A thành màn C")
    for _ in range(3):
        assert stop(ws, t, tmp_path)["decision"] == "block"
    last = stop(ws, t, tmp_path)
    assert "decision" not in last and "WITHOUT passing" in last["systemMessage"]


def test_rejecting_needs_a_reason_and_is_shown(ws, tmp_path):
    setup(ws, tmp_path)
    f = ws / "output" / "est.xlsx"
    book(f, "Đổi màn quay về của màn A thành màn B")
    _, out = gate(ws, tmp_path, "check", f)
    answer(ws, tmp_path, out["next"], [{"unit": "明細!A2", "type": "unclear", "problem": "p", "rewrite": "r"}])
    gate(ws, tmp_path, "check", f)
    code, out = gate(ws, tmp_path, "resolve", f, "I1", "rejected")
    assert code == 2 and "reason" in out["error"]
    gate(ws, tmp_path, "resolve", f, "I1", "rejected", "--reason", "ô gốc của khách, không sửa")
    code, out = gate(ws, tmp_path, "check", f)
    assert code == 0 and "ô gốc của khách, không sửa" in out["summary"]


def test_only_changed_units_are_reviewed_against_the_original(ws, tmp_path):
    setup(ws, tmp_path)
    orig, f = ws / "output" / "v1.xlsx", ws / "output" / "v2.xlsx"
    book(orig)
    book(f, "Đổi màn quay về của màn A thành màn B")
    _, out = gate(ws, tmp_path, "check", f, "--original", orig)
    assert out["to_review"] == 1
    prompt = next((ws / ".brse" / "gate").glob("*.prompt.md")).read_text()
    assert "before: Hỗ trợ màn A" in prompt


def test_a_reply_the_agent_writes_itself_is_refused(ws, tmp_path):
    setup(ws, tmp_path)
    for tool_input in ({"file_path": str(ws / ".brse" / "gate" / "x.reply.json")},):
        r = run_cli("hook", "guard", stdin=json.dumps({"cwd": str(ws), "tool_name": "Write", "tool_input": tool_input}),
                    tmp=tmp_path)
        assert r.returncode == 2
    r = run_cli("hook", "guard", stdin=json.dumps({"cwd": str(ws), "tool_name": "Bash",
                                                   "tool_input": {"command": "echo {} > .brse/gate/x.reply.json"}}),
                tmp=tmp_path)
    assert r.returncode == 2
    r = run_cli("hook", "guard", stdin=json.dumps({"cwd": str(ws), "tool_name": "Bash",
                                                   "tool_input": {"command": "python3 brse.py gate check out.xlsx"}}),
                tmp=tmp_path)
    assert r.returncode == 0


def test_writing_into_client_sources_is_refused(ws, tmp_path):
    r = run_cli("hook", "guard", stdin=json.dumps({"cwd": str(ws), "tool_name": "Edit",
                                                   "tool_input": {"file_path": str(ws / "src-docs" / "spec.md")}}),
                tmp=tmp_path)
    assert r.returncode == 2 and "source documents" in r.stderr
    r = run_cli("hook", "guard", stdin=json.dumps({"cwd": str(ws), "tool_name": "Edit",
                                                   "tool_input": {"file_path": str(ws / "notes.md")}}), tmp=tmp_path)
    assert r.returncode == 0


def test_report_delivered_through_subagent_handback_is_captured(ws, tmp_path):
    """Newer Claude Code: the Agent result only says 'agentId: <id>'; the report is in the subagent's transcript."""
    setup(ws, tmp_path)
    f = ws / "output" / "est.xlsx"
    book(f, "Đổi màn quay về của màn A thành màn B")
    _, out = gate(ws, tmp_path, "check", f)
    prompt = out["next"].split('"')[1]
    main = tmp_path / "sess.jsonl"
    main.write_text("")
    sub = tmp_path / "sess" / "subagents"
    sub.mkdir(parents=True)
    issues = {"issues": [{"unit": "明細!B2", "type": "unclear", "problem": "p", "rewrite": "r"}]}
    (sub / "agent-abc123.jsonl").write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in [
        {"type": "user", "message": {"role": "user", "content": prompt}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "SubagentHandback",
                                                       "input": {"message": json.dumps(issues, ensure_ascii=False)}}]}},
    ]))
    hook = {"cwd": str(ws), "tool_name": "Agent", "transcript_path": str(main),
            "tool_input": {"subagent_type": "brse-toolkit:wording-reviewer", "prompt": prompt},
            "tool_response": {"content": [{"type": "text", "text": "report delivered as a message\nagentId: abc123"}]}}
    run_cli("hook", "agent-done", stdin=json.dumps(hook), tmp=tmp_path)
    code, out = gate(ws, tmp_path, "check", f)
    assert code == 1 and out["open_issues"][0]["unit"] == "明細!B2"


def test_re_review_shows_the_earlier_issue_for_that_unit(ws, tmp_path):
    setup(ws, tmp_path)
    f = ws / "output" / "est.xlsx"
    book(f)
    _, out = gate(ws, tmp_path, "check", f)
    answer(ws, tmp_path, out["next"], [{"unit": "明細!B2", "type": "vague", "problem": "không nói đổi gì",
                                        "rewrite": "x"}])
    gate(ws, tmp_path, "check", f)
    book(f, "Đổi màn quay về của màn A thành màn B")
    gate(ws, tmp_path, "resolve", f, "I1", "fixed")
    gate(ws, tmp_path, "check", f)
    prompt = next((ws / ".brse" / "gate").glob("*.prompt.md")).read_text()
    assert "earlier review: vague — không nói đổi gì → answered closed" in prompt


def test_office_text_fills_an_empty_translation_column(ws, tmp_path):
    src, out = ws / "output" / "v1.xlsx", ws / "output" / "v1_vi.xlsx"
    (ws / "output").mkdir(exist_ok=True)
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "明細"
    sh["B2"], sh["C3"] = "画面Aの戻る先を画面Bに変更", "đã có"
    sh["B3"] = "画面C追加"
    wb.save(src)
    (ws / "tr.json").write_text(json.dumps({"明細!B2": "Đổi màn quay về của màn A thành màn B"}, ensure_ascii=False))
    r = run_cli("office-text", "apply", src, ws / "tr.json", out, ws, "--to-column", "C", cwd=ws)
    assert r.returncode == 0, r.stdout
    got = openpyxl.load_workbook(out)["明細"]
    assert got["B2"].value == "画面Aの戻る先を画面Bに変更" and got["C2"].value == "Đổi màn quay về của màn A thành màn B"
    (ws / "tr.json").write_text(json.dumps({"明細!B3": "Thêm màn C"}, ensure_ascii=False))
    r = run_cli("office-text", "apply", src, ws / "tr.json", out, ws, "--to-column", "C", cwd=ws)
    assert r.returncode == 2 and "already holds text" in r.stdout


def test_editing_before_the_check_still_records_the_review(ws, tmp_path):
    """Seen in the trial: the agent read the reviewer's answer and edited the cell before running check."""
    setup(ws, tmp_path)
    f = ws / "output" / "est.xlsx"
    book(f)
    _, out = gate(ws, tmp_path, "check", f)
    answer(ws, tmp_path, out["next"], [{"unit": "明細!B2", "type": "vague", "problem": "không nói đổi gì",
                                        "rewrite": "Đổi màn quay về của màn A thành màn B"}])
    book(f, "Đổi màn quay về của màn A thành màn B")  # edited first
    code, out = gate(ws, tmp_path, "check", f)
    assert code == 1 and out["to_review"] == 1  # only the changed cell goes back to the reviewer
    st = json.loads(next(p for p in (ws / ".brse" / "gate").glob("*.json") if "." not in p.stem).read_text())
    assert st["issues"][0]["status"] == "closed" and st["issues"][0]["problem"] == "không nói đổi gì"


def test_style_notes_on_an_already_fixed_unit_do_not_block(ws, tmp_path):
    setup(ws, tmp_path)
    f = ws / "output" / "est.xlsx"
    book(f)
    _, out = gate(ws, tmp_path, "check", f)
    answer(ws, tmp_path, out["next"], [{"unit": "明細!B2", "type": "vague", "problem": "p", "rewrite": "r"}])
    gate(ws, tmp_path, "check", f)
    book(f, "Đổi màn quay về của màn A thành màn B")
    _, out = gate(ws, tmp_path, "check", f)
    answer(ws, tmp_path, out["next"], [{"unit": "明細!B2", "type": "unnatural", "problem": "lặp chữ màn",
                                        "rewrite": "Đổi đích quay về của A sang B"}])
    code, out = gate(ws, tmp_path, "check", f)
    assert code == 0 and out["advice"][0]["problem"] == "lặp chữ màn" and "style advice" in out["summary"]
    # a meaning problem on the same unit still blocks
    book(f, "Đổi màn quay về của màn A thành màn C")
    _, out = gate(ws, tmp_path, "check", f)
    answer(ws, tmp_path, out["next"], [{"unit": "明細!B2", "type": "mismatch", "problem": "B thành C",
                                        "rewrite": "Đổi màn quay về của màn A thành màn B"}])
    code, out = gate(ws, tmp_path, "check", f)
    assert code == 1 and out["open_issues"][0]["type"] == "mismatch"


def test_report_in_handback_field_of_the_agent_result_is_captured(ws, tmp_path):
    """Shape of the Agent tool result in Claude Code 2.1.3xx (report in handbackReport)."""
    setup(ws, tmp_path)
    f = ws / "output" / "est.xlsx"
    book(f, "Đổi màn quay về của màn A thành màn B")
    _, out = gate(ws, tmp_path, "check", f)
    prompt = out["next"].split('"')[1]
    issues = {"issues": [{"unit": "明細!B2", "type": "ambiguous", "problem": "p", "rewrite": "r"}]}
    hook = {"cwd": str(ws), "tool_name": "Agent",
            "tool_input": {"subagent_type": "brse-toolkit:wording-reviewer", "prompt": prompt},
            "tool_response": {"status": "completed", "agentId": "a1", "handback": "send",
                              "handbackReport": {"text": json.dumps(issues, ensure_ascii=False)},
                              "content": [{"type": "text", "text": "This agent's report was delivered to you"}]}}
    run_cli("hook", "agent-done", stdin=json.dumps(hook), tmp=tmp_path)
    code, out = gate(ws, tmp_path, "check", f)
    assert code == 1 and out["open_issues"][0]["type"] == "ambiguous"


def test_prompt_carries_client_document_passages_for_the_unit(ws, tmp_path):
    setup(ws, tmp_path)
    (ws / "src-docs" / "spec.md").write_text("# 画面A\n確定後の戻る先: 画面B一覧画面（変更）\n", encoding="utf-8")
    assert run_cli("kb-ingest", ws, tmp=tmp_path, cwd=ws).returncode == 0
    f = ws / "output" / "est.xlsx"
    wb = openpyxl.Workbook()
    sh = wb.active
    sh.title = "明細"
    sh["A2"], sh["B2"] = "確定後の戻る先を画面B一覧画面に変更", "Đổi màn quay về"
    wb.save(f)
    gate(ws, tmp_path, "check", f)
    prompt = next((ws / ".brse" / "gate").glob("*.prompt.md")).read_text()
    assert "document: src-docs/spec.md" in prompt and "画面B一覧画面（変更）" in prompt


def test_an_untouched_template_copy_does_not_block(ws, tmp_path):
    import shutil
    t = setup(ws, tmp_path)
    (ws / "templates").mkdir()
    book(ws / "templates" / "tpl.xlsx")
    cfg = json.loads((ws / ".brse" / "config.json").read_text())
    cfg["paths"]["templates"] = ["templates/"]
    (ws / ".brse" / "config.json").write_text(json.dumps(cfg))
    shutil.copy(ws / "templates" / "tpl.xlsx", ws / "output" / "est.xlsx")
    assert stop(ws, t, tmp_path) is None
    book(ws / "output" / "est.xlsx", "Đổi màn quay về của màn A thành màn B")
    assert stop(ws, t, tmp_path)["decision"] == "block"


def test_stop_ignores_translated_copies_outside_the_project(ws, tmp_path):
    """A copy recorded elsewhere (another folder, a deleted test file) never blocks this session."""
    t = setup(ws, tmp_path)
    store = ws / ".brse" / "checks.json"
    other = tmp_path / "elsewhere.xlsx"
    other.write_bytes(b"x")
    store.write_text(json.dumps({str(other): {"source": None, "applied_at": time.time() + 5, "check": None},
                                 "/tmp/gone/out.xlsx": {"source": None, "applied_at": time.time() + 5, "check": None}}))
    assert stop(ws, t, tmp_path) is None
