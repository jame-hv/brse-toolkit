# brse-toolkit 3.0.0 — kiểm tra do code giữ, không do lời dặn

Ngày: 2026-11-12. Thay cho cách vận hành ở mục 4–6 của
`2026-08-02-brse-toolkit-design.md`; mục 2 (vai trò) và mục 3 (bộ nhớ) giữ nguyên.

## 1. Vấn đề

Đến bản 2.2.0, plugin là lời dặn trong các tệp SKILL.md cộng một bộ lệnh
`brse.py`. Lời dặn ghi "bắt buộc", nhưng code chỉ chặn hai việc: mở tệp chứa
khóa API, và kết thúc lượt khi bản dịch ghi bằng `office-text apply` chưa qua
`translation-check`. Mọi bước khác do model tự giác.

Khi dùng thật cho một sheet ước lượng song ngữ, các lỗi sau đã lọt qua. Cột
bên phải ghi chỗ trong plugin không chặn được:

| Lỗi | Chỗ trong plugin |
|---|---|
| Chữ thật trong ô Excel đã ghi không được soát; bước soát chạy trên bản nháp | review-gate bảo model tự chép chữ ra tệp rồi soát tệp đó |
| Sửa sau khi soát rồi vẫn giao | không có dấu nào gắn với bản đã soát |
| Cột tiếng Việt do model tự viết, không qua bước dịch | skill ước lượng không gọi skill dịch |
| Cụm chỉ màn đích bị dịch sát chữ, đọc không hiểu | người soát chỉ thấy chữ tiếng Việt, không thấy câu gốc |
| Người soát đòi giải nghĩa chữ viết tắt trong ô ước lượng | quy tắc cấm viết tắt áp như nhau cho mọi loại tài liệu |
| Kết quả soát nhận về bị bỏ qua | không có gì bắt trả lời từng lỗi |
| Dòng việc viết cho một chức năng đã có ở bản spec cũ | không bước nào bắt so bản spec cũ với bản mới |
| Dòng việc chỉ ghi 「〜への対応」, không nói đổi gì | skill chỉ dặn "cụm danh từ ngắn" |
| Dòng việc không có căn cứ trong tài liệu khách vẫn nằm trong bản giao | "không có con số nào thiếu căn cứ" chỉ là lời dặn |
| Người dùng chỉ ra lỗi, model giải thích rồi hỏi xin phép sửa | lời dặn "dừng, trình bày, chờ đồng ý" không phân biệt chốt giai đoạn với lỗi được chỉ ra |

Bộ kiểm thử không bắt được những lỗi này: các test chỉ kiểm từng lệnh riêng
lẻ, không bài chạy thử nào làm sheet ước lượng hay dịch sheet.

## 2. Mục tiêu

1. Model làm phần cần đầu óc (đọc, viết, dịch, phán đoán). Code chạy kiểm tra
   trên tệp thật và chặn kết thúc lượt khi chưa qua.
2. Chữ đem soát được đọc từ chính tệp kết quả.
3. Tệp đổi sau khi soát thì kết quả soát hết hiệu lực.
4. Mọi lỗi người soát báo đều có câu trả lời: đã sửa (tệp đổi và được soát
   lại) hoặc bác kèm lý do, và lý do bác hiện trong bản tóm tắt khi giao.
5. Người soát thấy câu gốc, đoạn tài liệu khách liên quan và các lần sửa đã ghi.
6. Thông báo "chưa qua chốt" đến thẳng người dùng, không qua lời tóm tắt của model.

## 3. Không làm

- Không viết chương trình chạy ngoài Claude Code. Các điểm móc của Claude Code
  (trước khi dùng công cụ, sau khi dùng công cụ, khi kết thúc lượt, khi bắt
  đầu phiên) đủ để chặn.
- Code không chấm chất lượng câu chữ. Code chỉ bảo đảm việc soát chạy trên
  đúng chữ thật, đủ ngữ cảnh, và không lỗi nào bị bỏ im.

## 4. Điều không được xảy ra

- Chặn liên tục đến mức không làm việc được: mỗi lần chặn nêu đúng lệnh chạy tiếp.
- Model tự viết kết quả soát thay người soát.
- Kết thúc lượt khi chưa qua chốt mà người dùng không biết.

## 5. Đã làm

### 5.1 Chốt trên tệp thật — `brse.py gate`

`gate check <tệp> [--original <tệp gốc>] [--kind estimate-cell|text]`:

1. Đọc từng đơn vị chữ (ô, đoạn, đoạn trong slide, nhãn sơ đồ) từ tệp kết quả.
   Có tệp gốc thì chỉ lấy đơn vị đã đổi.
2. Ghép mỗi đơn vị với ô bên cạnh (trong bảng song ngữ là ô câu gốc), đoạn tài
   liệu khách có nhắc tới tên trong đơn vị đó (tra kho knowledge), tin nhắn của
   người dùng trong phiên, các mục trong `feedback-log.md`, quy ước và thuật ngữ.
3. Gửi người soát (mục 5.3). Mỗi lỗi phải được trả lời: sửa đơn vị trong tệp
   (lần kiểm tra sau thấy chữ đổi, đóng lỗi và soát lại chữ mới) hoặc
   `gate resolve <tệp> <mã> rejected --reason "..."`.
4. Không còn lỗi mở và mọi đơn vị đã được soát với chữ hiện tại thì ghi dấu:
   mã băm sha256 của tệp. Tệp đổi thì dấu hết hiệu lực.

Góp ý chỉ về văn phong (`unnatural`, `translated-feel`) trên một đơn vị đã sửa
một lần thì chỉ để tham khảo, không chặn. Căn cứ: khi chạy thử, người soát đảo
ngược góp ý văn phong của chính nó qua nhiều vòng (bảo bỏ một chữ, vòng sau đòi
thêm lại) và chốt không bao giờ qua. Lỗi về nghĩa vẫn chặn.

### 5.2 Chặn kết thúc lượt

Điểm móc khi kết thúc lượt tìm mọi tệp Office và `.drawio` trong dự án có giờ
sửa sau lúc phiên bắt đầu, trừ thư mục tài liệu khách, thư mục mẫu và `.brse`.
Tệp chưa có dấu hợp lệ thì không cho kết thúc. Bản sao chưa sửa của một tệp mẫu
hoặc tài liệu khách không cần dấu.

Claude Code cần lối ra để không chặn mãi: sau 3 lần chặn liên tiếp, lượt được
kết thúc nhưng điểm móc gửi thông báo thẳng cho người dùng (`systemMessage`).

Bản dịch ghi bằng `office-text apply` vẫn phải qua `translation-check`, và chỉ
tính bản dịch còn tồn tại trong dự án của phiên.

### 5.3 Người soát

- Có model thứ hai (`review.second_agent`) thì code gọi thẳng.
- Không có thì code ghi đề vào `.brse/gate/` và in lệnh gọi agent con
  `wording-reviewer` (soát chữ) hoặc `reviewer` (chấm điểm theo tiêu chí).
  Điểm móc sau khi dùng công cụ `Agent` lấy câu trả lời từ kết quả của công cụ
  (`handbackReport`) và lưu cạnh đề. Kết quả soát ghi tay không được nhận:
  điểm móc trước khi dùng công cụ chặn mọi lệnh ghi vào `.brse/gate/`.

### 5.4 Quy tắc theo loại sản phẩm — `config/deliverable-kinds.json`

- `estimate-cell`: cụm danh từ ngắn, cùng độ chi tiết với ô gốc, nêu đối tượng
  và thay đổi; 「〜への対応」, 「〜追加」 đứng một mình là mơ hồ; chữ viết tắt
  có trong bảng thuật ngữ được dùng.
- `text`: câu đầy đủ, không viết tắt, con số thay cho lượng mơ hồ.

Loại mới chỉ được thêm khi có căn cứ ghi kèm.

### 5.5 Quy trình ước lượng — `brse.py run`

`run start estimate --file <bản sao ước lượng>`, rồi `run status` liệt kê bước
chưa đạt và lệnh cần chạy. `gate check` không ghi dấu cho tệp ước lượng khi
còn bước chưa đạt.

| Bước | Điều kiện |
|---|---|
| sources | có `manifest.json`; mọi tệp chỉ đọc được một phần hoặc không đọc được đều được ghi là đã đọc bằng mắt, hoặc lý do chưa đọc (`run read`) |
| versions | tài liệu có nhiều phiên bản (tên có `_v2`, `Rev.3`, `第2版`...) phải được khai cặp cũ – mới (`run pair`) |
| requirements | mỗi yêu cầu R- có `source` (vị trí ở bản mới) và `old_source` (vị trí ở bản cũ, hoặc `none` khi là mới), trỏ tới tệp có thật |
| approved | người dùng đã nhắn sau khi danh sách yêu cầu sẵn sàng, rồi model ghi `run approve` |
| rows | mỗi ô việc trong cột khai báo trỏ tới một yêu cầu trong phạm vi; mỗi yêu cầu trong phạm vi có một dòng |

Chốt duyệt chỉ có ở bước approved. Lỗi người dùng chỉ ra trong lúc làm được
sửa ngay rồi báo lại, không hỏi xin phép.

### 5.6 Khởi tạo không hỏi — `brse.py init`

Tên dự án, thư mục tài liệu khách, thư mục mẫu, thư mục nội bộ, thư mục đã gửi
khách và ngôn ngữ khách được suy ra từ tên thư mục và tên tệp. Tham số dòng
lệnh ghi đè. Khối CLAUDE.md còn khoảng 25 dòng.

### 5.7 Khác

- `office-text apply --to-column C`: điền vào cột dịch đang trống của sheet.
- Test `test_no_client_words_in_repo_files`: dò chữ cấm trong mọi tệp của repo;
  danh sách chữ cấm nằm ngoài repo (`~/.config/brse-toolkit/forbidden-words.txt`).
- Test chạy với thư mục dữ liệu riêng và không để lại tệp tạm.

## 6. Chưa làm

- Gộp các skill chồng nhau, tách `anatomy` khỏi plugin.
- Đưa bài chạy thử ước lượng song ngữ (spec cũ và mới, một chức năng đã có từ
  bản cũ) vào `evals/`.

## 7. Giới hạn

- Code không ép được model thật sự nhìn ảnh chụp trang.
- Chất lượng bản dịch vẫn do người soát quyết định; người soát là agent con
  cùng model thì không độc lập, và bản tóm tắt ghi rõ điều đó.
- Sau 3 lần chặn, lượt vẫn kết thúc được, kèm thông báo cho người dùng.
