---
name: init
description: Scaffold documents/, templates/, memory/, CLAUDE.md for a new BrSE project in the current directory
---

Run the following steps in the current directory (the user's project directory, NOT the plugin repo):

1. If `memory/` already exists — stop, ask the user whether to overwrite, do not continue on your own.
2. Create the directories: `documents/`, `templates/`, `memory/`.
3. Create `templates/README.md` with this content:
   "Put the client's own report/slide/DD templates here (font, colors, column structure). The report-gen/detail-design-jp skills read files from this directory when present, and fall back to defaults otherwise."
4. Create `documents/README.md` with this content:
   "Put the client's source documents here (spec, DD, test case lists, emails, meeting notes) — this is the input side, read by cross-check/code-to-business/proposal-gen/etc. Commit each version the client sends as its own commit, so cross-check can diff old vs new via git history (see spec section 3) — don't overwrite a file in place without committing the prior version first."
5. Create 4 files in `memory/`, each with only a title line + schema guidance (empty, no real data yet — except `glossary.md`, which is seeded with a common IT/BrSE starter vocabulary, see below). Written in English so the scaffolding is readable by any team; actual entries (translations, decisions, etc.) get filled in whatever language the project's deliverables use:

   `memory/parties.md`:
   ```
   # Parties — who is who in this project

   Entry schema:
   - <Party name> — role: <client/vendor/our team/...> — default form of address: <not yet confirmed — use neutral pronouns (e.g. formal "we"/"you") until confirmed>
   ```

   `memory/glossary.md`: entry schema `- EN: <term> | VI: <term> | JP: <term> — <source note, or "khởi tạo mặc định" for the seeded starter entries below>`. Matching in `check-glossary.py` fires on the VI or JP form (jp-vi-translate only translates between those two) — EN is carried along as the standard reference term. Seed the file with:

   ```
   # Glossary EN-VI-JP

   Entry schema:
   - EN: <term> | VI: <term> | JP: <term> — <source note>

   Starter vocabulary — common IT/BrSE terms, not client-specific decisions.
   A project's own confirmed terms (from QA, spec, decisions-log) OVERRIDE
   these on conflict — update the entry in place rather than adding a
   duplicate, and change its source note to the real source once confirmed.

   - EN: screen | VI: màn hình | JP: 画面 — khởi tạo mặc định
   - EN: field | VI: trường | JP: フィールド — khởi tạo mặc định
   - EN: button | VI: nút | JP: ボタン — khởi tạo mặc định
   - EN: requirement | VI: yêu cầu (nghiệp vụ) | JP: 要件 — khởi tạo mặc định
   - EN: specification | VI: đặc tả | JP: 仕様 — khởi tạo mặc định
   - EN: basic design | VI: thiết kế cơ bản | JP: 基本設計 — khởi tạo mặc định
   - EN: detailed design | VI: thiết kế chi tiết | JP: 詳細設計 — khởi tạo mặc định
   - EN: test case | VI: trường hợp kiểm thử | JP: テストケース — khởi tạo mặc định
   - EN: unit test | VI: kiểm thử đơn vị | JP: 単体テスト — khởi tạo mặc định
   - EN: integration test | VI: kiểm thử tích hợp | JP: 結合テスト — khởi tạo mặc định
   - EN: regression test | VI: kiểm thử hồi quy | JP: 回帰テスト — khởi tạo mặc định
   - EN: acceptance test | VI: kiểm thử nghiệm thu | JP: 受入テスト — khởi tạo mặc định
   - EN: bug | VI: lỗi | JP: バグ — khởi tạo mặc định
   - EN: defect | VI: lỗi (khiếm khuyết) | JP: 不具合 — khởi tạo mặc định
   - EN: environment | VI: môi trường | JP: 環境 — khởi tạo mặc định
   - EN: server | VI: máy chủ | JP: サーバ — khởi tạo mặc định
   - EN: client | VI: máy khách | JP: クライアント — khởi tạo mặc định
   - EN: database | VI: cơ sở dữ liệu | JP: データベース — khởi tạo mặc định
   - EN: table | VI: bảng | JP: テーブル — khởi tạo mặc định
   - EN: column | VI: cột | JP: カラム — khởi tạo mặc định
   - EN: row | VI: dòng | JP: 行 — khởi tạo mặc định
   - EN: deploy | VI: triển khai | JP: デプロイ — khởi tạo mặc định
   - EN: release | VI: phát hành | JP: リリース — khởi tạo mặc định
   - EN: version | VI: phiên bản | JP: バージョン — khởi tạo mặc định
   - EN: validation | VI: kiểm tra hợp lệ | JP: バリデーション — khởi tạo mặc định
   - EN: error message | VI: thông báo lỗi | JP: エラーメッセージ — khởi tạo mặc định
   - EN: login | VI: đăng nhập | JP: ログイン — khởi tạo mặc định
   - EN: logout | VI: đăng xuất | JP: ログアウト — khởi tạo mặc định
   - EN: session | VI: phiên làm việc | JP: セッション — khởi tạo mặc định
   - EN: user | VI: người dùng | JP: ユーザー — khởi tạo mặc định
   - EN: permission | VI: quyền | JP: 権限 — khởi tạo mặc định
   - EN: confirmation | VI: xác nhận | JP: 確認 — khởi tạo mặc định
   - EN: update | VI: cập nhật | JP: 更新 — khởi tạo mặc định
   - EN: create/register | VI: tạo mới | JP: 新規作成 — khởi tạo mặc định
   - EN: delete | VI: xóa | JP: 削除 — khởi tạo mặc định
   - EN: edit | VI: chỉnh sửa | JP: 編集 — khởi tạo mặc định
   - EN: search | VI: tìm kiếm | JP: 検索 — khởi tạo mặc định
   - EN: filter | VI: lọc | JP: 絞り込み — khởi tạo mặc định
   - EN: sort | VI: sắp xếp | JP: 並び替え — khởi tạo mặc định
   - EN: pagination | VI: phân trang | JP: ページング — khởi tạo mặc định
   - EN: upload | VI: tải lên | JP: アップロード — khởi tạo mặc định
   - EN: download | VI: tải xuống | JP: ダウンロード — khởi tạo mặc định
   - EN: batch process | VI: xử lý theo lô | JP: バッチ処理 — khởi tạo mặc định
   - EN: log | VI: nhật ký | JP: ログ — khởi tạo mặc định
   - EN: backup | VI: sao lưu | JP: バックアップ — khởi tạo mặc định
   - EN: security | VI: bảo mật | JP: セキュリティ — khởi tạo mặc định
   - EN: authentication | VI: xác thực | JP: 認証 — khởi tạo mặc định
   - EN: authorization | VI: phân quyền | JP: 認可 — khởi tạo mặc định
   - EN: encryption | VI: mã hóa | JP: 暗号化 — khởi tạo mặc định
   - EN: interface | VI: giao diện | JP: インターフェース — khởi tạo mặc định
   - EN: function | VI: chức năng | JP: 機能 — khởi tạo mặc định
   - EN: performance | VI: hiệu năng | JP: パフォーマンス — khởi tạo mặc định
   - EN: workflow | VI: quy trình làm việc | JP: ワークフロー — khởi tạo mặc định
   - EN: ticket | VI: phiếu yêu cầu | JP: チケット — khởi tạo mặc định
   - EN: milestone | VI: mốc tiến độ | JP: マイルストーン — khởi tạo mặc định
   - EN: deadline | VI: hạn chót | JP: 締切 — khởi tạo mặc định
   ```

   This is a common-vocabulary starting point, not an exhaustive industry glossary — extend it the same way as any other confirmed term (spec section 3): append an entry in the same `EN: ... | VI: ... | JP: ...` format when a new term gets settled.

   `memory/conventions.md`:
   ```
   # Conventions — ad-hoc formatting conventions

   Entry schema:
   - <format description, e.g. "red text in Excel sheet X"> → <confirmed meaning> — source: <file>, confirmed <date>
   ```

   `memory/decisions-log.md`:
   ```
   # Decisions log — overlay on top of the official DD/spec

   Entry schema:
   - Decision: <content, state the scope of applicability clearly>
     Source: QA #<id>, date <date>
     Status in the official doc: <FULLY updated / PARTIALLY updated / NOT YET updated>
   ```

6. Create `CLAUDE.md` at the project root (if it doesn't exist yet — if it does, append instead of overwriting):

   ```markdown
   ## brse-toolkit memory

   Before running any brse-toolkit skill, read `memory/parties.md`,
   `memory/glossary.md`, `memory/conventions.md`, `memory/decisions-log.md`.

   When new information surfaces (a term, a convention, a relationship between parties,
   a QA decision) — confirm it with the user in one short sentence, then **write it to
   the corresponding file immediately**, before moving on to other work. Don't batch
   confirmations and write them all at the end of the session — the conversation can get
   compacted, the file can't.

   ## brse-toolkit — how to behave toward the end user

   This plugin's users are BrSEs, not developers — they can't read raw tool
   calls/output.

   - Received a passage/file with no clear instruction on what to do with it (e.g. a
     pasted Japanese passage with no accompanying instruction) — **stop and ask first**,
     don't guess: "Translate, cross-check, or something else?". If it's a translation,
     also ask for the target language (default JP→VI, but confirm if unclear). Only
     pick a skill on your own once the intent is clearly stated.
   - Before running a skill, subagent, or script — say one short plain-language sentence
     describing what you're about to do (e.g. "Using the jp-vi-translate skill to
     translate this passage", "Splitting 3 emails into 3 parallel subagents"). Don't
     dump the raw tool call/command in front of the user.
   ```

   (This injected block configures the project's own `CLAUDE.md`, addressed to whoever
   works in that project — keep it in English for the same reason as the memory files
   above, regardless of what language the project's deliverables end up in.)

7. Check whether the current directory is already a git repo (`git rev-parse --is-inside-work-tree`).
   If not, run `git init` — the anti-staleness mechanism in `cross-check` needs git
   history to retrieve prior versions when comparing documents.
8. Report back to the user: done, list the files/directories just created.
