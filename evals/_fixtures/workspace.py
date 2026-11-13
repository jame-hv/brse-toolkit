"""Build a synthetic brse-toolkit workspace for an eval case (no client data).

Usage: python3 workspace.py <plugin_root> <kind>   (run inside the empty eval workspace)
kind: diagram | ingest | intent
"""
import json
import sys
from pathlib import Path

import docx
import openpyxl

ROOT, KIND = Path(sys.argv[1]), sys.argv[2]
W = Path.cwd()


def base():
    (W / ".brse/memory/long").mkdir(parents=True)
    (W / ".brse/memory/short").mkdir(parents=True)
    (W / "documents").mkdir()
    cfg = {"layout_version": 2,
           "project": {"name": "demo-order", "client_language": "ja", "team_language": "vi"},
           "paths": {"sources": ["documents/"], "outputs": "output/"}}
    (W / ".brse/config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (W / ".brse/config.local.json").write_text('{"project": {"reply_language": "vi"}}', encoding="utf-8")
    for name, title in [("parties", "Parties"), ("glossary", "Glossary EN-VI-JP"), ("conventions", "Conventions"),
                        ("decisions-log", "Decisions log"), ("feedback-log", "Feedback log"),
                        ("deliverables-log", "Deliverables log")]:
        (W / f".brse/memory/long/{name}.md").write_text(f"# {title}\n", encoding="utf-8")
    # the project CLAUDE.md block exactly as `brse.py init` writes it, values filled for this project
    sys.path.insert(0, str(ROOT))
    from brse.project.init import BLOCK
    block = BLOCK.format(name="demo-order", sources="documents/", templates="none", client_language="ja",
                         reply_language="vi")
    (W / "CLAUDE.md").write_text(block + "\n", encoding="utf-8")


def spec_docx():
    d = docx.Document()
    d.add_heading("受注システム 現行システム構成", level=1)
    for line in [
        "営業担当者は社内PCのブラウザから受注画面を利用する。",
        "受注画面はWebサーバ（受注Web）を経由してAPIサーバ（受注API）に登録要求を送る。",
        "受注APIは受注データを受注DB（PostgreSQL）に登録する。",
        "毎日22時に夜間バッチが受注DBから出荷指示CSVを作成し、SFTPで外部の倉庫管理システム（WMS）へ送信する。",
        "受注APIは登録完了時にメールサーバ経由で営業担当者へ完了メールを送る。",
    ]:
        d.add_paragraph(line)
    d.save(W / "documents/現行システム構成.docx")


def screen_xlsx():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "受注登録"
    ws.append(["No", "項目名", "型", "必須", "桁数", "備考"])
    for row in [[1, "顧客コード", "文字", "○", 8, "顧客マスタに存在すること"],
                [2, "受注日", "日付", "○", 10, "初期値: システム日付"],
                [3, "商品コード", "文字", "○", 10, ""],
                [4, "数量", "数値", "○", 5, "1以上"],
                [5, "備考", "文字", "", 200, ""]]:
        ws.append(row)
    wb.save(W / "documents/画面定義_受注登録.xlsx")


def estimate_and_qa():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "見積"
    ws.append(["No", "作業項目", "対象数", "工数(人日)", "備考"])
    for row in [[1, "画面改修", 4, 20, "受注登録・受注一覧・受注詳細・顧客検索"],
                [2, "API改修", 3, 9, ""],
                [3, "データ移行", 1, 10, "旧受注データ移行"],
                [4, "結合テスト", 1, 8, ""]]:
        ws.append(row)
    ws.append(["", "合計", "", "=SUM(D2:D5)", ""])
    wb.save(W / "documents/見積_v1.xlsx")
    qa = openpyxl.Workbook()
    q = qa.active
    q.title = "QA"
    q.append(["No", "質問", "回答", "回答日"])
    q.append([1, "改修対象の画面数を教えてください。", "受注登録・受注一覧・受注詳細・顧客検索・出荷状況照会の5画面です。", "2026-11-05"])
    q.append([2, "旧システムのデータ移行は今回の範囲に含まれますか。", "データ移行は弊社で実施するため、今回の範囲外です。", "2026-11-05"])
    q.append([3, "API改修の対象数を教えてください。", "3本です。", "2026-11-05"])
    qa.save(W / "documents/QA一覧_回答済.xlsx")


base()
{"diagram": spec_docx, "ingest": screen_xlsx, "intent": estimate_and_qa}[KIND]()
