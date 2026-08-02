# brse-toolkit — Claude Code plugin design (v2)

Thay thế `docs/poc.md`. Bản này là kết quả sau khi rà lại poc.md bằng ví dụ thật (dịch email khách Nhật, đọc Excel có ảnh embedded, xưng hô relay...) và fix những chỗ poc.md gốc bỏ sót.

## 1. Mục tiêu & nguyên tắc

- Phục vụ công việc BrSE hàng ngày: dịch, đối chiếu spec, phân tích code/nghiệp vụ, tạo report, quản lý Q&A.
- Ưu tiên cao nhất: độ tin cậy output — phải giải trình được từng câu chữ với khách/PM.
- Mọi skill kết luận phải kèm nguồn/bằng chứng cụ thể. Không skill nào được kết luận suông.
- **Không tự gán quan hệ/xưng hô/quy ước nếu chưa được xác nhận** — mặc định trung tính hoặc hỏi lại, không đoán.
- Fact-check (trích nguồn) tách riêng khỏi văn bản tự nhiên (bản dịch/proposal) — không nhét traceability vào giữa câu văn làm hỏng độ tự nhiên.
- Kiến trúc: skill nhỏ, đơn nhiệm, chain được với nhau, có script deterministic đứng sau cho phần cần chính xác tuyệt đối (không để model tự "nhìn" mà đoán những gì script đọc được chính xác).

## 2. Mô hình vai trò — BrSE là relay, không phải máy dịch trung lập

Đây là phát hiện quan trọng nhất khi rà lại thiết kế: BrSE luôn đứng giữa ít nhất 2-3 bên (khách Nhật, công ty mình, dev VN). Một bản "dịch" không phải là ánh xạ câu-sang-câu trung lập — nó là **relay thông tin qua ranh giới ngôn ngữ + vai trò**, phải biết:

1. Văn bản nguồn là **ai nói** (khách? dev? PM?)
2. Output này **để cho ai đọc** (dev VN? khách Nhật? cả 2 bên đều đọc?)

Hệ quả cụ thể:
- Đại từ nhân xưng trong câu gốc (私たち/chúng tôi) **không được dịch nguyên** khi relay sang phía khác — phải đổi thành tên bên cụ thể (vd "bên Sanyu", "team mình") để người đọc không hiểu nhầm là chính họ.
- Câu xin phép/mềm hóa giọng điệu kiểu Nhật (ご了承いただければ) khi relay cho dev nên chuyển thành hành động cụ thể dev cần làm, không dịch nguyên văn phong xin phép.
- Không có config xác nhận về quan hệ giữa các bên → mặc định xưng hô trung tính ("chúng tôi"/"quý vị"), không tự chọn "em/anh/chị" ngụ ý cấp bậc.

Mọi skill động tới ngôn ngữ (`jp-vi-translate`, `qa-tone-brse`, phần trích spec trong `cross-check`, `proposal-gen`) bắt buộc phải resolve 2 câu hỏi trên trước khi chạy — thông tin này lấy từ `memory/parties.md` (mục 3), nếu file chưa có thì phải hỏi, không chạy mặc định "dịch xuôi".

## 3. Bộ nhớ theo dự án — `memory/` (trục chính của toàn bộ plugin)

Đây là phần quan trọng nhất, không phải add-on. Nếu không có bộ nhớ bền theo dự án, plugin không có lợi thế gì so với dùng claude.ai web trực tiếp — giá trị cốt lõi của plugin nằm ở đây, các skill chỉ là người đọc/ghi vào nó.

### Cấu trúc

Nằm **trong thư mục dự án cụ thể của khách/dự án anh đang làm** (không nằm trong repo plugin). Cả 3 thư mục đều **visible**, không dùng dot-folder — mọi thứ user có thể cần mở ra xem/sửa tay đều phải dễ tìm, không giấu:

```
<thư mục dự án>/
├── CLAUDE.md            # Claude Code tự động nạp mỗi session, không cần trigger
├── documents/            # tài liệu gốc thật (spec, DD, Excel khách cung cấp) — tên tùy ý,
│                            không bắt buộc "documents", giữ nguyên cấu trúc anh đang có
├── templates/             # mẫu report/DD riêng của khách — user tự bỏ file vào tay,
│                            skill chỉ đọc, không tự ghi vào đây
├── memory/                # derived data — tool tự sinh/tự cập nhật sau khi user xác nhận
│   ├── parties.md        # ai là ai, quan hệ, cách xưng hô giữa các bên
│   ├── glossary.md        # thuật ngữ JP-VI đã chốt (用語 | 訳語 | 種別 | 備考)
│   ├── conventions.md     # quy ước format phát sinh (màu đỏ, gạch ngang nghĩa gì...)
│   └── decisions-log.md   # quyết định/QA đã chốt chính thức, trích dẫn trỏ path vào documents/
└── (code repo, nếu `code-to-business` cần — path riêng, có thể nằm ngoài thư mục này,
     memory/parties.md ghi rõ path trỏ tới đâu, không giả định code luôn nằm cùng chỗ)
```

**Ai tạo cấu trúc này:** không bắt user tự tay mkdir. Plugin có 1 slash command `/brse-toolkit:init` (trong `commands/init.md`, xem mục 7) — chạy 1 lần khi bắt đầu dự án mới trong 1 thư mục, tự tạo `documents/`, `templates/` (kèm 1 README ngắn giải thích bỏ gì vào), `memory/` với 4 file `.md` có sẵn schema mẫu (rỗng, chưa có dữ liệu thật), `CLAUDE.md` trỏ tới `memory/`, **và tự `git init` nếu thư mục chưa phải git repo** (không để user tự nhớ làm việc này — cơ chế chống-stale ở dưới phụ thuộc vào git history). User không cần biết trước cấu trúc, chỉ cần chạy lệnh này 1 lần.

`CLAUDE.md` chỉ cần 1 đoạn ngắn: trỏ tới `memory/`, yêu cầu mọi skill đọc trước khi chạy, và nếu phát hiện thông tin mới → xác nhận 1 câu ngắn với user → **tự ghi vào file tương ứng**, không hỏi lại ở session sau.

**Rule cứng — ghi NGAY, không trì hoãn:** ngay sau khi user xác nhận 1 fact (dù chỉ 1 câu ngắn), hành động tiếp theo ngay lập tức phải là ghi vào `memory/*.md` — trước khi làm việc khác, không gộp nhiều xác nhận lại ghi 1 lần cuối session. Lý do: Claude Code tự nén (compact) hội thoại khi context dài ra — nén là lossy. Fact chỉ tồn tại trong hội thoại (chưa ghi ra file) có thể mất chính xác khi bị nén, và không cách nào lấy lại. File trên đĩa không bị ảnh hưởng bởi việc nén hội thoại — 1 khi đã ghi, an toàn vĩnh viễn bất kể agent chạy thêm bao lâu hay session kết thúc thế nào. Cửa sổ rủi ro duy nhất là khoảng hở giữa lúc xác nhận và lúc ghi file — rule này ép khoảng hở đó về gần bằng 0. Hệ quả: không cần giữ 1 agent chạy xuyên suốt nhiều ngày để "không mất context" — bắt đầu session mới cho mỗi khối công việc là bình thường, không mất gì vì `memory/` là file, không phải hội thoại.

**Yêu cầu hạ tầng để cơ chế chống-stale hoạt động được:** `documents/` (và `memory/`) nên nằm trong 1 git repo riêng tư theo dự án (khác repo plugin) — mỗi lần khách gửi bản spec/DD mới, commit lại. `cross-check` lấy version cũ từ git history để so với bản mới, không cần anh tự giữ nhiều file trùng tên `spec_v2.xlsx`/`spec_v3.xlsx`. Không có git ở đây thì mục "Chống stale khi tài liệu nguồn được update" bên dưới không có cách nào lấy lại bản cũ để so.

### Chống stale khi tài liệu nguồn được update

Mỗi entry trong `memory/*.md` phải ghi kèm nguồn + version/ngày, không ghi trần trụi:

```
- 登録 → "Lưu" (không phải "Đăng ký", theo context màn hình Save) — nguồn: spec.xlsx v2, P45, xác nhận 2026-07-20
```

Khi `cross-check` phát hiện file nguồn có version mới, nó quét `memory/` tìm entry đang trỏ về phần đã đổi trong bản cũ → gắn nhãn "cần re-verify". Không tự tin dùng tiếp, không tự xóa — chờ xác nhận lại.

### `decisions-log.md` là lớp phủ lên doc chính thức (DD/spec), không chỉ là log

Thực tế hay gặp: khách quyết định qua QA (chat/Excel Q&A list) nhưng **không update DD/spec đầy đủ** — DD chỉ phản ánh 1 phần quyết định, hoặc không phản ánh gì. Nếu skill nào cũng chỉ tin DD là đủ, sẽ bỏ sót quyết định thật.

Schema bắt buộc cho mỗi entry trong `decisions-log.md`:

```
- Quyết định: <nội dung quyết định, ghi rõ phạm vi áp dụng>
  Nguồn: QA #<id>, ngày <date>
  Trạng thái trong doc chính thức: <ĐÃ update đầy đủ / CHỈ update 1 phần (ghi rõ phần nào) / CHƯA update>
```

**Rule bắt buộc cho mọi skill đọc DD/spec** (`code-to-business`, `detail-design-jp`, `cross-check`, và cả khi BrSE tự hỏi "spec nói gì về X"): phải check `decisions-log.md` trước, không coi nội dung DD là đầy đủ. Nếu có entry liên quan mà "Trạng thái trong doc chính thức" khác "ĐÃ update đầy đủ" → phải trình bày cả 2 lớp: DD viết gì (và viết ở đâu) + quyết định thật theo QA khác gì/rộng hơn gì so với DD.

Khi DD/spec được update thật sau này, `cross-check` so lại với các entry đang ở trạng thái "CHỈ update 1 phần"/"CHƯA update" — entry nào DD đã bắt kịp thì đổi trạng thái, entry nào chưa thì tiếp tục flag, không để nó rơi khỏi tầm nhìn.

### Tách biệt khỏi repo plugin

`memory/` là dữ liệu riêng theo dự án/khách, **không bao giờ nằm trong repo brse-toolkit** (repo plugin generic, share/public được vì không chứa tên khách nào). Giải quyết luôn rủi ro lộ thông tin khách nếu repo plugin từng công khai.

### Giới hạn thật

Nếu công việc không gắn với 1 thư mục dự án cụ thể (hỏi nhanh, ad-hoc, không lặp lại) — không có nơi neo `memory/`, plugin không có lợi thế so với claude.ai web. Chỉ dùng plugin cho công việc lặp lại theo dự án có thật.

### Khi thư mục chưa tồn tại — rule chung cho mọi skill đụng tới `documents/`/`templates/`/`memory/`

Trước khi chạy, skill check 3 thư mục này có tồn tại chưa. 2 trường hợp, xử lý khác nhau, không gộp chung:

- **Chỉ thiếu 1 thư mục phụ (vd `templates/`), `memory/` vẫn có** — vô hại, tự tạo thư mục trống, dùng mặc định cho lần này, báo 1 dòng rõ ràng. Không cần hỏi.
- **Thiếu `memory/`** (chưa từng chạy `/brse-toolkit:init`, hoặc dự án mới tự phát) — **không được** âm thầm chạy tiếp như bình thường. Không có `memory/` nghĩa là không lưu lại được gì cho lần sau — nếu skill lặng lẽ dùng mặc định, output vẫn ra nhưng user không biết là lần này không có gì được nhớ. Phải dừng lại, hỏi thẳng: "Dự án chưa init (thiếu `memory/`) — chạy `/brse-toolkit:init` trước để lưu được cho lần sau, hay tiếp tục 1 lần không lưu gì?" — không tự quyết thay user.

## 4. Danh sách skill — 3 giai đoạn

**Giai đoạn 1 — Nền tảng**
1. `verify-output` — chính sách bắt buộc, xem mục 6.1
2. `cross-check` — đối chiếu nhiều loại nguồn + phát hiện `memory/` bị stale, xem mục 6.2
3. `jp-vi-translate` — dịch JP-VI, có mô hình relay (mục 2), xem mục 6.6
4. `qa-tone-brse` — trả lời Q&A đúng kênh (chat/Excel Q&A list), quản lý luôn QA log, xem mục 6.7

**Giai đoạn 2 — Phân tích chuyên sâu**
5. `code-to-business` — trích nghiệp vụ từ source code, trỏ đúng file:line, xem mục 6.10
6. `excel-analyze` — đọc cell + ảnh embedded + shape, xem mục 6.3
7. `image-analyze` — OCR trước, vision sau, xem mục 6.4

**Giai đoạn 3 — Tổng hợp & Output**
8. `report-gen` — xuất Excel/Slide/Word đúng template khách, xem mục 6.9 (ví dụ luồng tạo slide)
9. `brainstorm-brse` — đề xuất phương án có trade-off
10. `research-jp-tech` — research ưu tiên nguồn tiếng Nhật, note ngày nguồn, xem mục 6.12
11. `proposal-gen` — requirements → proposal (bản nội bộ kỹ thuật + bản khách), xem mục 6.8
12. `detail-design-jp` — DD theo khung SI Nhật chuẩn hoặc template khách, xem mục 6.11

Quản lý nhiều dự án/nhiều document nói chung — không làm thành 1 skill riêng. Giải qua bằng cấu trúc `memory/` theo từng thư mục dự án (mục 3); phần quản lý Q&A cụ thể đã gộp vào `qa-tone-brse`.

## 5. Script bắt buộc theo từng skill

| Skill | Script | Vì sao cần (không để model tự đoán) |
|---|---|---|
| `verify-output` | `lint-hedge-words.py` | Quét regex tìm từ cấm ("có lẽ", "chắc là"...) + kiểm mỗi kết luận có tag `(nguồn: ...)`, chặn trước khi xuất |
| `cross-check` | `diff-structured.py` + adapter riêng theo loại nguồn (code/spec/Excel không cùng dạng) | So sánh thật bằng diff, không để Claude "nhìn" 2 file dài rồi tự so bằng mắt |
| `jp-vi-translate`, `qa-tone-brse` | `check-glossary.py`, `check-consistency.py` | Quét term đối chiếu `memory/glossary.md`; quét cả file dịch phát hiện 1 term bị dịch 2 kiểu khác nhau |
| `code-to-business` | `extract-refs.py` (ripgrep/ast) | Lấy đúng file:line, không đọc nguyên codebase vào context, không để Claude tự nhớ số dòng |
| `excel-analyze` | `extract-cells.py`, `extract-images.py`, fallback render sheet→PNG (LibreOffice headless) | Đọc cell/màu/gạch ngang chính xác từ XML; ảnh/shape không đọc structured được thì render ảnh, chain sang `image-analyze` |
| `image-analyze` | `ocr-pass.py` (Tesseract + gói `jpn`) | Chữ in/UI text để OCR đọc, chính xác hơn vision đoán; vision chỉ lo layout/mũi tên/chữ viết tay |
| `report-gen` | dùng `openpyxl`/`python-pptx`/`python-docx` | Cần template file thật, không tạo từ số 0 |

Các skill không cần script riêng: `brainstorm-brse`, `research-jp-tech`, `proposal-gen`, `detail-design-jp` (chain qua các skill có script ở trên).

## 6. Chi tiết kỹ thuật đã chốt qua rà soát

### 6.1 `verify-output` — chính sách cụ thể

- Liệt kê từng câu kết luận trong draft response.
- Mỗi câu kết luận phải có tag nguồn: `(nguồn: file:dòng)` / `(nguồn: sheet, ô)` / `(nguồn: spec trang X)`.
- Không gắn được nguồn → viết "chưa xác định được — cần hỏi khách", không viết như sự thật.
- Cấm từ mơ hồ trong kết luận: "có lẽ", "chắc là", "hình như", "có thể" (không cấm khi đang hỏi lại khách).
- `lint-hedge-words.py` kiểm tự động trước khi xuất câu trả lời cuối.

### 6.2 `cross-check` — đối chiếu nhiều loại nguồn khác nhau

Ba loại cặp nguồn, mỗi loại cần adapter parse riêng trước khi diff được — không giả định 2 nguồn luôn cùng dạng:
- **Spec cũ vs spec mới** (cùng dạng Excel/Word): parse cả 2 thành field/điều kiện, diff thật (không phải Claude "nhìn" 2 file rồi so bằng mắt) → liệt kê field bị xóa/thêm/đổi giá trị.
- **Code vs spec**: lấy logic thực tế từ code (qua `code-to-business`) đối chiếu mô tả trong spec → phát hiện spec nói có nhưng code không làm, hoặc ngược lại.
- **Excel vs Excel**: so theo key column, phát hiện dòng thiếu/trùng/giá trị lệch.

**Giới hạn thật:** chỉ so được phần đã parse thành structure (field/key-value). Phần văn xuôi tự do (mô tả nghiệp vụ dạng đoạn văn) không so structured được — phải hạ xuống so câu-với-câu, độ tin cậy thấp hơn hẳn, output phải nói rõ đang dùng chế độ nào (structured diff hay text diff), không trình bày 2 loại ngang hàng.

Vai trò kép của `cross-check`: ngoài so 2 nguồn, còn là cơ chế phát hiện `memory/` bị stale (mục 3) và đối chiếu `decisions-log.md` với DD khi DD được update (mục 3).

### 6.3 `excel-analyze` — xử lý file "bẩn" (định dạng, ảnh, shape)

- Cell value + font.color + font.strike + fill.color + comment → đọc chính xác qua `openpyxl` (structured, không phải vision).
- Ý nghĩa của định dạng (đỏ = gì, gạch ngang = gì) **không đoán** — lần đầu quan sát pattern rồi hỏi xác nhận, lưu vào `memory/conventions.md`, lần sau áp dụng luôn không hỏi lại. Ô có định dạng lạ chưa từng xác nhận → flag riêng.
- Ảnh dán trong sheet: `worksheet._images` lấy được bytes + vùng ô neo (không phải 1 ô chính xác, mà là 1 vùng — phải nói rõ giới hạn này khi trích dẫn).
- Shape/textbox/mũi tên annotation: `openpyxl` không đọc đầy đủ được — fallback render cả sheet thành PNG (LibreOffice headless), chain sang `image-analyze`.
- Report cuối gộp 2 loại nguồn, không trình bày ngang hàng: phần cell-text (chính xác tuyệt đối) và phần ảnh/shape (qua vision, gắn rõ nhãn "đọc bằng ảnh, chưa chắc 100%").

### 6.4 `image-analyze`

- OCR pass trước (Tesseract + `jpn`) cho chữ in/UI text — đáng tin hơn để vision tự đọc.
- Vision chỉ đảm nhiệm phần OCR không làm được: bố cục, hướng mũi tên, chữ viết tay.
- Luôn gắn confidence rõ ràng, không trình bày ngang hàng với structured data từ script.

### 6.5 Encoding

- File `.txt`/`.csv`/code cũ (đặc biệt tiếng Nhật) có thể là Shift-JIS, không phải UTF-8 — script đọc file text phải tự detect encoding (`chardet`, thử `cp932` trước khi fallback UTF-8), không mặc định UTF-8.
- File `.xlsx` không bị vấn đề này (nội bộ luôn lưu UTF-8 trong XML, kể cả file cũ).

### 6.6 `jp-vi-translate` — sửa lại mô hình 2-pass sau khi test thật

Mô hình "pass 1 dịch sát nghĩa + pass 2 tự nhiên hóa" **chỉ áp dụng cho field/thuật ngữ cố định** (dùng qua `check-glossary.py`). Áp dụng cách này cho văn xuôi/email/QA sinh ra bản dịch translationese (đã test thật, kết quả tệ hơn máy dịch thông thường — xem log hội thoại thiết kế).

Với văn xuôi/email/QA, quy trình đúng:
1. Đọc hết đoạn để hiểu **mục đích giao tiếp**, không dịch từng mệnh đề.
2. Dịch thẳng theo nghĩa + đúng giọng văn Việt business, **không bám ranh giới câu/cấu trúc mệnh đề tiếng Nhật** (không dịch literal các từ đệm mềm hóa giọng điệu kiểu というか/ということです).
3. Áp mô hình relay (mục 2) cho đại từ nhân xưng và ngữ khí.
4. Fact-check tách riêng: liệt kê fact/quyết định chính (không phải từng câu) kèm nguồn, đặt sau bản dịch, không nhét giữa câu văn.
5. Từ chêm vào chỉ để câu tiếng Việt có ngữ pháp đúng (không map được về token nguồn) — nếu bắt buộc phải thêm, đánh dấu rõ (vd ngoặc vuông), không để lẫn như thể có nguồn.

### 6.7 `qa-tone-brse` — quản lý QA log

File Q&A list Excel gửi khách **chính là** sổ theo dõi QA nội bộ — không tách state riêng. Khi có câu hỏi mới: đọc lại toàn bộ Q&A list hiện có (dùng `extract-cells.py`), so với câu hỏi mới (text similarity đơn giản) → nếu giống câu đã trả lời, báo lại thay vì trả lời khác đi lần 2; câu mới thật → soạn theo tone kênh tương ứng, append vào file.

### 6.8 `proposal-gen` — audience quyết định nội dung, không chỉ trình bày

Khác với `report-gen` (chỉ lo phần trình bày/format), `proposal-gen` phải tự áp mô hình relay (mục 2) ngay ở bước soạn **nội dung**: bản nội bộ kỹ thuật giữ chi tiết/thuật ngữ kỹ thuật đầy đủ; bản gửi khách phải giản lược, không dùng thuật ngữ nội bộ chưa giải thích, không dịch nguyên xưng hô như mục 2 đã nói. 2 bản là 2 lần soạn nội dung khác nhau, không phải 1 bản rồi rút gọn cơ học.

### 6.9 `report-gen` — ví dụ luồng cụ thể khi cần tạo slide

Ca cụ thể: BrSE gõ "tạo slide báo cáo tình trạng tuần này" hoặc "tạo slide đề xuất giải pháp cho vấn đề X". Luồng xử lý:

1. **Xác định nội dung lấy từ đâu** — không tự bịa nội dung slide. Tùy loại yêu cầu:
   - Status report → kéo từ `memory/decisions-log.md` (quyết định/thay đổi gần đây) + kết quả `cross-check`/`code-to-business` nếu có phân tích liên quan.
   - Đề xuất giải pháp → chain qua `proposal-gen` trước để có nội dung đã cấu trúc (scope, trade-off), `report-gen` chỉ lo phần trình bày.
   - Nếu user cung cấp nội dung trực tiếp trong yêu cầu → dùng nội dung đó, vẫn áp bước 3 bên dưới.
2. **Xác định template** — check `templates/` xem có mẫu slide riêng của khách chưa (font, màu, cấu trúc). Có thì dùng `python-pptx` mở template đó và điền nội dung vào, giữ nguyên design. Chưa có → dùng mẫu mặc định đơn giản, và phải nói rõ trong response: "chưa có template khách, dùng mẫu mặc định — xác nhận format sau."
3. **Xác định người đọc slide** — áp mô hình relay (mục 2): slide gửi khách Nhật khác slide báo cáo nội bộ PM/dev (mức độ kỹ thuật, xưng hô, ngôn ngữ JP/VI). Chưa rõ đối tượng đọc → hỏi trước khi soạn, không mặc định.
4. **Áp verify-output cho từng bullet trên slide** — mỗi gạch đầu dòng có claim/số liệu phải có nguồn. Không gắn được nguồn → không đưa thẳng lên slide, để trong speaker notes dạng "cần xác nhận thêm" thay vì trình bày như fact đã chốt (rủi ro cao hơn text thường vì slide thường đi thẳng tới khách, ít qua bước review kỹ).
5. **Script tạo file thật** (`python-pptx`) → xuất `.pptx`.
6. **Output trả về**: file `.pptx` + danh sách ngắn "giả định/điểm chưa xác nhận" tách riêng để anh duyệt trước khi gửi — không lẫn vào trong slide.

### 6.10 `code-to-business` — chiến lược đọc codebase lớn

1. Không nhận yêu cầu mơ hồ kiểu "phân tích toàn bộ codebase" — bắt buộc có phạm vi cụ thể (1 tính năng/luồng nghiệp vụ). Chưa rõ phạm vi → hỏi lại, không tự chọn đại.
2. `extract-refs.py` grep theo keyword nghiệp vụ trong phạm vi đó (ripgrep/ast) → trả về danh sách file:line, không đổ nguyên file vào context.
3. Từ danh sách match, chỉ đọc (Read tool, đúng đoạn dòng liên quan) những file/hàm thực sự nằm trong luồng — không đọc hết mọi file có match.
4. Codebase lớn, logic rải nhiều file (khoảng >10 file) → xử lý từng file/module một, ghi nhận phát hiện vào bản nháp trung gian, tổng hợp ở bước cuối — không nhồi tất cả vào 1 lượt đọc.
5. Match tìm được nhưng không chắc liên quan → liệt kê riêng "tìm thấy nhưng chưa chắc liên quan, cần xác nhận" — không tự loại, không tự gộp vào kết luận chính.

### 6.11 `detail-design-jp` — nguồn nội dung và tính đầy đủ

- Nội dung lấy từ `code-to-business` (nếu viết DD từ code có sẵn) + `memory/decisions-log.md` (quyết định/requirements đã chốt) — không tự bịa nội dung kỹ thuật.
- Mọi mục trong khung chuẩn (改訂履歴, 概要/目的, 処理概要+フロー, 画面レイアウト+項目定義, 入力チェック, テーブル定義, エラー処理) phải có nội dung hoặc ghi rõ "không áp dụng/chưa có thông tin" — không được âm thầm bỏ trống 1 mục mà không giải thích.
- Có template khách trong `templates/` → dùng thay khung mặc định trong plugin (xem ghi chú phân biệt 2 loại template ở mục 7), giữ nguyên cấu trúc khách quen dùng.

### 6.12 `research-jp-tech` — quy trình cụ thể

- Ưu tiên nguồn theo thứ tự: domain chính phủ/tổ chức Nhật (`.go.jp`, hiệp hội ngành) → tài liệu hãng (nếu research công nghệ cụ thể) → blog kỹ thuật uy tín → nguồn tiếng Anh/Việt bổ sung sau cùng.
- Mỗi kết luận phải kèm URL + ngày truy cập (áp `verify-output`) — không tóm tắt rồi bỏ nguồn.
- Kết quả liên quan tới quy ước/quyết định của dự án đang làm → hỏi có lưu vào `memory/decisions-log.md` không, tránh phải research lại lần sau cho cùng 1 vấn đề.

## 7. Cấu trúc thư mục plugin

```
brse-toolkit/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json          # optional, chỉ cần nếu tự host marketplace
├── skills/
│   ├── verify-output/{SKILL.md, scripts/lint-hedge-words.py}
│   ├── cross-check/{SKILL.md, scripts/diff-structured.py}
│   ├── jp-vi-translate/{SKILL.md, scripts/check-glossary.py, scripts/check-consistency.py}
│   ├── qa-tone-brse/SKILL.md
│   ├── code-to-business/{SKILL.md, scripts/extract-refs.py}
│   ├── excel-analyze/{SKILL.md, scripts/extract-cells.py, scripts/extract-images.py}
│   ├── image-analyze/{SKILL.md, scripts/ocr-pass.py}
│   ├── report-gen/SKILL.md
│   ├── brainstorm-brse/SKILL.md
│   ├── research-jp-tech/SKILL.md
│   ├── proposal-gen/SKILL.md
│   └── detail-design-jp/{SKILL.md, templates/detail-design-jp-template.md}
│       # LƯU Ý: đây là template MẶC ĐỊNH đóng gói sẵn trong plugin (generic, public-safe,
│       # dùng khi dự án chưa có mẫu riêng) — khác với `templates/` trong mục 3, là mẫu
│       # RIÊNG của từng khách nằm trong thư mục dự án. 2 khái niệm trùng tên, không trùng chỗ.
├── commands/
│   └── init.md                     # bắt buộc — scaffold documents/, templates/, memory/, CLAUDE.md
│                                      trong thư mục dự án hiện tại, chạy 1 lần khi bắt đầu dự án mới
├── agents/                         # optional
├── .mcp.json                       # optional
└── README.md
```

`memory/` **không** nằm trong repo này — xem mục 3.

## 8. Deployment

Claude Code plugin, dùng cho chính người dùng chính (BrSE) hàng ngày — bắt buộc vì phần lớn skill cần chạy script thật qua Bash tool, các hình thức khác (Claude Project web, app riêng) không đáp ứng được yêu cầu độ tin cậy đã đặt ra ở mục 1.

Cài local: `claude plugin install ./brse-toolkit`.

Chia sẻ cho đồng nghiệp (nếu cần sau này): push repo plugin lên git (an toàn vì không chứa `memory/`), đồng nghiệp `claude plugin marketplace add` + `install`. Vẫn yêu cầu đồng nghiệp có Claude Code (CLI/IDE extension) — chưa có giải pháp cho người dùng hoàn toàn không dùng Claude Code, việc này **để ngoài phạm vi** bản thiết kế này.

## 9. Rủi ro

| Vấn đề | Ảnh hưởng | Xử lý |
|---|---|---|
| `memory/` chứa tên khách hàng | Rò rỉ nếu lẫn vào repo plugin | Tách hoàn toàn — `memory/` sống trong thư mục dự án riêng, không commit vào repo plugin |
| `memory/` bị stale khi tài liệu update | Dùng quy ước/quyết định cũ sai | Mỗi entry ghi nguồn+version, `cross-check` flag khi phát hiện version đổi (mục 3) |
| Dịch/QA gán sai xưng hô/quan hệ giữa các bên | Hiểu nhầm ai nói gì, ai chịu trách nhiệm | Mô hình relay bắt buộc (mục 2), mặc định trung tính nếu chưa xác nhận |
| Excel/ảnh có định dạng ý nghĩa riêng theo khách | Suy đoán sai ý nghĩa màu/gạch ngang | Không đoán, xác nhận 1 lần, lưu `memory/conventions.md` (mục 6.3) |
| Skill quá lớn, tốn context dù không dùng | Tốn token mỗi session | `disable-model-invocation` cho skill ít dùng |
| Version plugin cập nhật liên tục | Đồng nghiệp cài bản cũ nếu tự host | Bump version mỗi lần sửa đáng kể |

## 10. Dữ liệu/công cụ thật cần có trước khi code (không thể tự resolve bằng thiết kế — cần từ phía anh)

Mọi quyết định thiết kế đã chốt xong ở mục 1-9. Danh sách dưới đây không phải lỗ hổng thiết kế còn thiếu, mà là input thật chỉ anh mới cung cấp được — không viết thêm chữ nào giải quyết được:

- 1 dự án/thư mục thật để chạy `/brse-toolkit:init` lần đầu và điền `memory/` bằng dữ liệu thật (parties, glossary) — mọi cơ chế ở mục 3 đã thiết kế xong, chỉ chưa chạy qua case thật.
- Công cụ hệ thống: LibreOffice (render sheet→ảnh), Tesseract + gói `jpn` (OCR) — cần cài trên máy trước khi build `excel-analyze`/`image-analyze`.
- Repo code cụ thể (ngôn ngữ gì) để chạy thử `code-to-business` (mục 6.10).
- Ít nhất 1 template slide/report/DD thật của khách để test `report-gen`/`detail-design-jp` — thiếu thì lần chạy đầu luôn rơi vào nhánh mặc định.

## 11. Mô hình thực thi — parallel theo đơn vị công việc độc lập, tuần tự trong 1 đơn vị

Bản trước tối ưu sai trọng tâm — thiên về an toàn context hơn tốc độ, trong khi pain point #1 ngay từ đầu là tốc độ ("mỗi ngày đi dịch thuật khá mất thời gian"). Lý do dùng AI ở đây là nén hàng giờ việc lặp lại (dịch nhiều email, phân tích nhiều file, trả lời nhiều Q&A) xuống còn vài phút — sửa lại đúng trọng tâm đó.

**Nguyên tắc: parallel theo đơn vị công việc độc lập (batch item), tuần tự chỉ trong 1 đơn vị.**

- 1 đơn vị = 1 email cần dịch, 1 file Excel cần phân tích, 1 câu Q&A cần trả lời, 1 module code cần trích nghiệp vụ, 1 nguồn cần research.
- Nhiều đơn vị độc lập trong cùng 1 yêu cầu (vd "dịch 20 email này", "phân tích 5 file Excel này", "trả lời 10 câu Q&A này") → dispatch **song song**, mỗi đơn vị 1 subagent riêng. Áp dụng cho mọi skill xử lý batch được: `jp-vi-translate`, `qa-tone-brse`, `excel-analyze`, `cross-check`, `code-to-business`, `research-jp-tech` — không giới hạn ở 1-2 skill.
- **Trong 1 đơn vị** (vd các câu trong cùng 1 email dài) vẫn tuần tự, cùng 1 context — câu sau cần biết câu trước đã xử lý thế nào để mạch lạc, xưng hô nhất quán (mô hình relay, mục 2). Tách nhỏ hơn nữa phá vỡ mạch, không lợi.

**Vai trò agent chính (coordinator):**
1. Nhận yêu cầu, phát hiện có phải batch nhiều đơn vị độc lập không — có thì tách, dispatch song song qua Agent/Task tool có sẵn của Claude Code (không tự xây orchestration riêng).
2. Mỗi subagent tự đọc `memory/` liên quan (glossary, parties) trước khi xử lý đơn vị của mình — chi phí thêm nhỏ (đọc vài file text), không đáng kể so với thời gian tiết kiệm được.
3. Gom kết quả từ tất cả subagent.
4. **Dedupe fact mới phát hiện**: nếu 2+ subagent cùng phát hiện 1 thuật ngữ/quy ước chưa có trong `memory/`, gộp lại hỏi user 1 lần — không hỏi lặp N lần cho cùng 1 thứ.
5. Sau khi user xác nhận, agent chính ghi vào `memory/` — vẫn 1 lần, tuần tự, đúng rule ghi-ngay ở mục 3. **Subagent không bao giờ tự ghi file `memory/`** — đây là cách duy nhất tránh race condition khi nhiều luồng song song cùng phát hiện 1 thứ rồi ghi đè lẫn nhau.
6. Tổng hợp kết quả cuối, trả về user dạng batch (vd 20 email đã dịch, kèm danh sách chung các điểm cần xác nhận thay vì 20 danh sách rời rạc).

**Đánh đổi, nói thẳng số:** parallel không tốn token nhiều hơn đáng kể — mỗi subagent vẫn chỉ làm đúng phần việc riêng (nội dung riêng của nó), phần dư chỉ là mỗi subagent tự đọc lại vài file `memory/` nhỏ (rẻ). Đổi lại thời gian chờ giảm từ N × (thời gian 1 đơn vị) xuống gần bằng 1 × (thời gian 1 đơn vị) khi chạy đủ song song — đây là điểm mấu chốt để việc dùng plugin nhanh hơn hẳn tự làm tay, không phải chỉ đỡ công gõ.
