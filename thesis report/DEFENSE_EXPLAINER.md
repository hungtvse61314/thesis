# RAEMatch — Giải thích từ số 0 (không cần biết trước kiến thức gì)

> Tài liệu này viết cho người **chưa biết gì về AI/ML/xử lý ngôn ngữ**. Mọi thuật ngữ đều được giải thích bằng ví dụ đời thường *trước khi* dùng ký hiệu toán học. Đọc từ trên xuống dưới, không bỏ qua phần nào, vì phần sau dùng lại khái niệm của phần trước.
>
> Xuyên suốt tài liệu, mình dùng **một ví dụ duy nhất** để bám theo: một Job Description (JD — tin tuyển dụng) và một CV, để anh thấy dữ liệu thật sự đi qua từng bước xử lý như thế nào, không chỉ là công thức trừu tượng.

---

## Phần 0 — Bài toán đang giải quyết là gì (không dùng thuật ngữ kỹ thuật)

Một công ty đăng tin tuyển "Senior Java Developer". Có 500 người nộp CV. Nhà tuyển dụng không có thời gian đọc hết 500 CV — họ cần một cách **xếp hạng** để đọc CV tốt nhất trước.

Cách làm cũ (keyword search): máy tính đếm xem CV nào chứa nhiều từ khóa trong tin tuyển dụng nhất (ví dụ "Java", "Spring Boot"). Vấn đề: một sinh viên mới ra trường có thể liệt kê đúng những từ đó trong CV (vì đã học ở trường) nhưng chưa từng đi làm ngày nào — máy tính vẫn xếp CV đó cao vì "trùng từ khóa", dù người đó rõ ràng không phù hợp với vị trí "Senior" (yêu cầu kinh nghiệm nhiều năm).

Cách làm mới hơn (mà luận văn gọi là "similarity-based" — dựa trên độ giống nhau tổng thể): thay vì đếm từ, máy tính "hiểu" nghĩa của cả đoạn văn CV và cả đoạn văn JD, rồi so sánh xem hai đoạn văn đó "giống nhau về ý nghĩa" đến mức nào. Cách này thông minh hơn đếm từ, nhưng vẫn còn vấn đề: nó cho ra **một con số duy nhất** đại diện cho "độ giống nhau chung chung", chứ không biết chính xác ứng viên có đáp ứng từng yêu cầu cụ thể hay không (VD: có đúng 5 năm kinh nghiệm không, có thực sự dùng Spring Boot trong công việc hay chỉ ghi ở phần "Kỹ năng" cho có).

**Ý tưởng của luận văn này**: Đừng chấm một con số chung chung. Hãy **tách JD thành từng yêu cầu riêng lẻ** (ví dụ: "phải biết Java", "phải biết Spring Boot", "phải có tối thiểu 5 năm kinh nghiệm", "nên biết Docker (không bắt buộc)"), rồi với **từng yêu cầu**, đi tìm trong CV xem có **bằng chứng cụ thể** hay không, và chỉ xếp hạng cao khi ứng viên đáp ứng đủ các yêu cầu *bắt buộc*.

Đây chính là lý do hệ thống được đặt tên **RAEMatch** = **R**equirement-**A**ware **E**vidence-aware **Match**ing (khớp CV-JD có nhận biết từng yêu cầu, và có kiểm tra bằng chứng).

---

## Phần 1 — Kiến thức nền cần biết trước khi đọc tiếp

### 1.1. "Vector" và "embedding" là gì?

Tưởng tượng anh muốn mô tả một người bằng vài con số, ví dụ: (chiều cao=170, cân nặng=65, tuổi=30). Đây là một **vector** — một danh sách các con số đại diện cho một thứ gì đó. Ba con số này giống như tọa độ của người đó trên "bản đồ 3 chiều".

Bây giờ thay vì mô tả người bằng chiều cao/cân nặng/tuổi, ta muốn mô tả **ý nghĩa của một câu văn** bằng một danh sách con số, sao cho **hai câu có nghĩa gần giống nhau thì có danh sách con số gần giống nhau**. Danh sách con số đó gọi là **embedding** (bản dịch sát nghĩa: "phép nhúng" — nhúng một câu văn vào một không gian tọa độ). Trong luận văn này, mỗi câu/đoạn văn được biến thành một danh sách gồm **384 con số** (gọi là "384 chiều") bằng một mô hình AI có sẵn tên là **all-MiniLM-L6-v2**. Anh không cần hiểu bên trong mô hình này hoạt động ra sao — chỉ cần biết: đưa 1 câu vào, nó trả ra 384 con số, và hai câu có nghĩa giống nhau sẽ có 2 dãy 384-số này "gần nhau".

### 1.2. "Gần nhau" giữa hai vector nghĩa là gì? — Cosine similarity

Nếu coi mỗi embedding là một **mũi tên** xuất phát từ gốc tọa độ, thì "hai câu giống nghĩa nhau" tương đương với "hai mũi tên chỉ cùng một hướng" (dù độ dài mũi tên khác nhau cũng không sao, ta chỉ quan tâm hướng).

**Cosine similarity** đo góc giữa hai mũi tên đó, quy về thang điểm:
- **1.0** = hai mũi tên chỉ đúng cùng một hướng (câu có nghĩa giống hệt nhau)
- **0.0** = hai mũi tên vuông góc nhau (không liên quan gì)
- Càng gần **1.0** thì hai câu càng "giống nghĩa" theo cách máy tính hiểu.

Đây là phép toán được dùng **ở khắp mọi nơi** trong luận văn để so sánh "câu này với câu kia giống nhau đến đâu".

### 1.3. TF-IDF là gì? (cách làm "đếm từ" thông minh hơn một chút)

TF-IDF là cách so khớp **dựa trên từ khóa xuất hiện**, không hiểu nghĩa. Nó đếm từ nào xuất hiện trong CV, nhưng có "thông minh" hơn đếm thô ở chỗ: từ nào **hiếm gặp** (ví dụ "Kubernetes") thì được coi trọng hơn từ **phổ biến** (ví dụ "the", "and", "kinh nghiệm"). Đây là phương pháp cũ (từ những năm 1980), nhanh, dễ hiểu, nhưng có nhược điểm: nếu CV viết "vi dịch vụ" thay vì "microservices" (cùng nghĩa nhưng khác chữ), TF-IDF sẽ coi hai câu đó **không liên quan** vì không chung chữ nào.

### 1.4. SBERT là gì? (cách làm "hiểu nghĩa" thay vì đếm chữ)

SBERT = Sentence-BERT, một loại mô hình AI biến câu văn thành **embedding** (mục 1.1), rồi dùng **cosine similarity** (mục 1.2) để so sánh nghĩa. SBERT hiểu được "vi dịch vụ" và "microservices" là gần nghĩa nhau dù khác chữ hoàn toàn — đây là điểm mạnh so với TF-IDF. Trong luận văn, cụm "SBERT full text" nghĩa là: lấy toàn bộ văn bản JD, biến thành 1 embedding; lấy toàn bộ văn bản CV, biến thành 1 embedding; rồi tính cosine similarity giữa hai embedding đó ra **một con số duy nhất**.

### 1.5. "Bài toán xếp hạng" (ranking problem) là gì?

Thay vì hỏi "CV này có phù hợp không" (đúng/sai), bài toán ở đây là: cho một JD và một danh sách hàng nghìn CV, hãy **sắp xếp** danh sách CV đó theo thứ tự từ phù hợp nhất đến ít phù hợp nhất. Đây gọi là **ranking** (xếp hạng). Người dùng cuối cùng chỉ xem top 10-20 CV đầu danh sách.

### 1.6. "Baseline" là gì?

Baseline là **phương pháp làm chuẩn để so sánh**. Nếu luận văn đề xuất một phương pháp mới, phải chứng minh nó tốt hơn (hoặc có ưu điểm khác) so với các phương pháp đã có sẵn (baseline). Trong luận văn này có 3 baseline: TF-IDF (mục 1.3), SBERT toàn văn bản (mục 1.4), và SBERT theo từng phần CV (Section-level SBERT — tính SBERT riêng cho mục Kỹ năng, riêng cho mục Kinh nghiệm, rồi lấy trung bình, thay vì gộp chung toàn bộ CV thành 1 embedding).

---

## Phần 2 — Ý tưởng cốt lõi: "Requirement decomposition" và "Evidence-aware matching"

### 2.1. Requirement decomposition — tách JD thành từng yêu cầu

Thay vì coi JD "Senior Java Developer, cần 5 năm kinh nghiệm, phải biết Java + Spring Boot, nên biết Docker" là **một đoạn văn**, hệ thống tách nó thành **danh sách các yêu cầu riêng lẻ**:

| Yêu cầu | Loại (bắt buộc/tùy chọn) | Nhóm |
|---|---|---|
| Java | bắt buộc (hard) | skill |
| Spring Boot | bắt buộc (hard) | skill |
| Docker | tùy chọn (soft) | skill |
| Tối thiểu 5 năm kinh nghiệm | bắt buộc (hard) | experience |
| Cấp bậc Senior | bắt buộc (hard) | seniority |

Đây gọi là **requirement decomposition** (phân rã yêu cầu). "Hard" = bắt buộc, không đạt là loại; "soft" = có thì cộng điểm, không có cũng không sao.

Trong luận văn, mỗi yêu cầu được viết dưới dạng một bộ ba `(t, c, w)`:
- `t` = nội dung yêu cầu (ví dụ chữ "Java")
- `c` = loại, chỉ có 2 giá trị: `hard` hoặc `soft`
- `w` = trọng số (mức độ quan trọng) — trong bản cài đặt hiện tại, `w` luôn = 1 cho mọi yêu cầu, nghĩa là **chưa phân biệt** "Java quan trọng hơn Git" trong cùng nhóm bắt buộc.

### 2.2. Evidence-aware matching — kiểm tra bằng chứng, không chỉ tin lời khai

Một CV có thể **liệt kê** "Spring Boot" trong mục Kỹ năng (Skills) mà **chưa từng thực sự dùng nó trong công việc** — nhiều người viết CV liệt kê hết mọi công nghệ họ từng nghe qua để "đẹp hồ sơ". Vì vậy hệ thống không tin ngay việc liệt kê — nó đi tìm **bằng chứng** trong phần "Kinh nghiệm làm việc" hoặc "Dự án" của CV.

Ví dụ: CV liệt kê "Spring Boot" trong Skills. Trong phần Kinh nghiệm làm việc, CV viết: *"Tôi đã xây dựng hệ thống microservices bằng Spring Boot cho công ty X"*. Hệ thống lấy câu này, biến thành embedding (mục 1.1), so sánh cosine similarity (mục 1.2) với embedding của yêu cầu "Spring Boot". Nếu độ giống nhau đủ cao → coi là **có bằng chứng thật** (evidenced). Nếu CV chỉ liệt kê "Spring Boot" trong Skills mà không câu nào trong Kinh nghiệm làm việc nhắc đến gì liên quan → coi là **chỉ khai báo suông** (unsupported).

Đây chính là ý nghĩa của "evidence-aware" (có nhận biết bằng chứng) trong tên hệ thống.

### 2.3. Bốn trạng thái của một yêu cầu — càng cụ thể càng đáng tin

Sau khi kiểm tra, mỗi yêu cầu của CV nhận đúng 1 trong 4 "nhãn":

1. **`satisfied` (đạt)**: có bằng chứng rõ ràng, độ giống nghĩa rất cao.
2. **`partially_satisfied` (đạt một phần)**: có liên quan nhưng chưa thật rõ ràng (độ giống nghĩa ở mức trung bình).
3. **`unsupported` (không có bằng chứng)**: được liệt kê ở mục Kỹ năng nhưng không tìm thấy câu nào trong Kinh nghiệm làm việc ủng hộ.
4. **`not_satisfied` (không đạt)**: không liệt kê, cũng không có bằng chứng gì cả.

Để máy tính có thể "tính toán" với 4 nhãn này (thay vì chỉ để đọc), mỗi nhãn được gán một con số:

```
satisfied           → 3 điểm
partially_satisfied → 2 điểm
unsupported         → 1 điểm
not_satisfied       → 0 điểm
```

**Lưu ý quan trọng (sẽ giải thích lại ở Phần 5)**: `unsupported` (1 điểm) vẫn **cao hơn 0**, tức là "khai láo" vẫn được cộng điểm ít nhiều so với "không khai gì" — đây là một điểm chưa hoàn hảo của thiết kế, sẽ giải thích kỹ ở Phần 5.4.

### 2.4. "Ngưỡng" (threshold) — ranh giới giữa các trạng thái

Độ giống nghĩa (cosine similarity, mục 1.2) là một con số liên tục từ 0 đến 1 (ví dụ 0.42, 0.67...). Để quyết định con số đó thuộc trạng thái nào trong 4 trạng thái ở mục 2.3, hệ thống đặt ra 2 **ngưỡng cắt**, gọi là τ_l (ngưỡng thấp) và τ_h (ngưỡng cao). Trong luận văn: τ_l = 0.35, τ_h = 0.55.

```
Nếu độ giống nghĩa ≥ 0.55            → satisfied
Nếu độ giống nghĩa từ 0.35 đến 0.55  → partially_satisfied
Nếu độ giống nghĩa < 0.35 (nhưng có khai báo)  → unsupported
Nếu không khai báo gì cả             → not_satisfied
```

Hai con số 0.35 và 0.55 này là **giá trị mặc định**, chưa qua tinh chỉnh kỹ trên dữ liệu thật — đây là một điểm hạn chế được nói rõ trong luận văn (xem Phần 6).

---

## Phần 3 — Cách hệ thống xếp hạng ứng viên: "Constraint-based reranking"

### 3.1. Vấn đề của cách xếp hạng "cộng điểm"

Cách đơn giản nhất để xếp hạng nhiều tiêu chí là **cộng điểm có trọng số**: ví dụ điểm cuối = 0.5×(độ giống Java) + 0.3×(độ giống kinh nghiệm) + 0.2×(độ giống Docker). Vấn đề: một ứng viên có thể có điểm "độ giống chung chung" rất cao (vì CV dài, nhiều từ liên quan) nhưng lại **hoàn toàn thiếu** một yêu cầu bắt buộc (ví dụ chưa từng dùng Spring Boot) — nếu cộng điểm, sự thiếu sót này có thể bị "điểm cao ở chỗ khác" che lấp, và ứng viên vẫn được xếp hạng cao một cách sai lầm.

### 3.2. Giải pháp: xếp hạng theo "từ điển" (lexicographic ranking)

Thay vì cộng điểm thành 1 số, hệ thống so sánh **từng tiêu chí theo thứ tự ưu tiên tuyệt đối**, giống như cách sắp xếp từ trong từ điển: so chữ cái đầu tiên trước, nếu bằng nhau mới so chữ thứ hai, cứ thế tiếp tục.

Áp dụng vào đây: **tiêu chí đầu tiên và quan trọng nhất là "có đạt hết mọi yêu cầu bắt buộc hay không"**. Chỉ khi hai ứng viên **bằng nhau** ở tiêu chí này, mới xét đến tiêu chí thứ hai, và cứ thế.

Cụ thể, mỗi ứng viên được gán một "chuỗi 7 con số" theo đúng thứ tự ưu tiên sau:

| Thứ tự | Ký hiệu | Ý nghĩa (giải thích bằng lời) | Cách tính |
|---|---|---|---|
| 1 (quan trọng nhất) | `H_pass` | Có đạt **toàn bộ** yêu cầu bắt buộc không? | 1 nếu tất cả yêu cầu `hard` đều ở trạng thái `satisfied`; ngược lại 0 |
| 2 | `C_h` | Trung bình mức độ đạt của các yêu cầu bắt buộc | Lấy điểm 0-3 mục 2.3 của từng yêu cầu hard, chia cho 3, rồi lấy trung bình |
| 3 | `E_h` | Bao nhiêu % yêu cầu bắt buộc có bằng chứng thật | số yêu cầu hard ở trạng thái satisfied/partially_satisfied, chia cho tổng số yêu cầu hard |
| 4 | `S_align` | Mức độ phù hợp về kinh nghiệm + cấp bậc | xem công thức Phần 4 |
| 5 | `C_s` | Giống C_h nhưng cho yêu cầu tùy chọn (soft) | |
| 6 | `E_s` | Giống E_h nhưng cho yêu cầu tùy chọn (soft) | |
| 7 (ít quan trọng nhất) | `B` | Độ giống nghĩa toàn văn bản (giống hệt cách tính SBERT ở mục 1.4) | chỉ dùng để **phân định khi mọi thứ ở trên đều hòa** |

**Cách đọc bảng này bằng lời, không cần công thức**: Ứng viên A đạt đủ mọi yêu cầu bắt buộc (`H_pass`=1), ứng viên B thiếu 1 yêu cầu bắt buộc (`H_pass`=0) — dù B có CV "đọc tổng thể giống JD hơn" (điểm `B` ở cột cuối cao hơn), A **vẫn luôn được xếp trên** B, vì `H_pass` được so sánh trước tiên và A đang thắng ở đó. Chỉ khi hai ứng viên **cùng đạt hết** yêu cầu bắt buộc, hệ thống mới nhìn tiếp xuống các tiêu chí phía sau để phân định ai hơn ai.

Đây chính là điểm khác biệt cốt lõi giữa cơ chế đề xuất và cách làm "cộng điểm" của SBERT/TF-IDF.

---

## Phần 4 — Kinh nghiệm và cấp bậc được so sánh như thế nào?

### 4.1. So sánh số năm kinh nghiệm

JD yêu cầu tối thiểu, ví dụ 5 năm. Ứng viên có, ví dụ 6 năm. Công thức:

```
Y_align = min(số năm ứng viên có / số năm JD yêu cầu, 1)
```

Ví dụ: ứng viên có 6 năm, JD cần 5 năm → 6/5 = 1.2, nhưng công thức chặn ở tối đa 1 (không cho vượt quá 1 dù thừa kinh nghiệm bao nhiêu) → `Y_align = 1.0`.
Nếu ứng viên chỉ có 3 năm: 3/5 = 0.6 → `Y_align = 0.6`.

### 4.2. So sánh cấp bậc (seniority)

Cấp bậc được xếp theo thứ tự: `Intern (thực tập) < Fresher (mới ra trường) < Junior < Middle < Senior < Lead < Architect`.

Gọi khoảng cách giữa cấp JD yêu cầu và cấp ứng viên đang có là Δ (đọc là "delta", nghĩa là "chênh lệch"):

```
Nếu ứng viên bằng hoặc cao hơn cấp JD yêu cầu → điểm = 1.0
Nếu ứng viên thấp hơn đúng 1 bậc              → điểm = 0.5
Nếu ứng viên thấp hơn từ 2 bậc trở lên        → điểm = 0.0
```

Ví dụ: JD cần Senior. Ứng viên A là Lead (cao hơn Senior) → điểm 1.0. Ứng viên B là Middle (thấp hơn Senior đúng 1 bậc) → điểm 0.5. Ứng viên C là Junior (thấp hơn Senior 2 bậc) → điểm 0.0.

### 4.3. Gộp hai điểm trên lại

```
S_align = (Y_align + L_align) / 2
```

Đơn giản là lấy trung bình cộng của "điểm kinh nghiệm" và "điểm cấp bậc" ở trên. Đây chính là thành phần thứ 4 trong bảng 7 tiêu chí ở Phần 3.2.

---

## Phần 5 — Ví dụ tính tay đầy đủ (một CV thật đi qua toàn bộ hệ thống)

**JD**: Senior Java Developer — bắt buộc: Java, Spring Boot; tùy chọn: Docker; tối thiểu 5 năm kinh nghiệm; cấp Senior.

**CV của ứng viên**: 6 năm kinh nghiệm, tự nhận cấp Senior. Mục Skills liệt kê: Java, Spring Boot, SQL. Mục Kinh nghiệm làm việc viết: *"Tôi đã xây dựng hệ thống microservices bằng Spring Boot"* — không có câu nào nhắc đến Java trực tiếp dù có liệt kê ở Skills. Không hề nhắc đến Docker.

**Bước 1 — Đánh giá từng yêu cầu:**

| Yêu cầu | Loại | Có trong Skills? | Có bằng chứng trong Kinh nghiệm? | Trạng thái | Điểm (mục 2.3) |
|---|---|---|---|---|---|
| Java | hard | Có | Không câu nào nhắc trực tiếp → giả sử độ giống nghĩa đo được là 0.20 (< 0.35) | `unsupported` | 1 |
| Spring Boot | hard | Có | Có, độ giống nghĩa đo được là 0.71 (≥ 0.55) | `satisfied` | 3 |
| Docker | soft | Không | Không | `not_satisfied` | 0 |
| ≥5 năm kinh nghiệm | hard | — | 6 ≥ 5 | `satisfied` | 3 |
| Cấp Senior | hard | — | Senior = Senior | `satisfied` | 3 |

**Bước 2 — Tính H_pass**: yêu cầu hard gồm Java, Spring Boot, kinh nghiệm, cấp bậc. Vì Java đang là `unsupported` (chưa `satisfied`) → **H_pass = 0** (fail!) — dù ứng viên này thực chất rất phù hợp, chỉ vì CV không viết rõ ràng "tôi dùng Java" trong phần Kinh nghiệm (có thể vì họ nghĩ Spring Boot đã ngầm hiểu là dùng Java).

Đây chính xác là loại tình huống mà luận văn phát hiện là **hạn chế thật của hệ thống** (đọc thêm Phần 6): một ứng viên rất tốt vẫn có thể bị đánh rớt gate chỉ vì CV không "viết lại" đúng cách mà máy tính mong đợi.

**Bước 3 — Tính C_h (trung bình mức đạt của yêu cầu hard)**:
```
C_h = (1/3 + 3/3 + 3/3 + 3/3) / 4 = (0.33 + 1 + 1 + 1) / 4 = 0.83
```
(chia mỗi điểm cho 3 vì thang điểm tối đa là 3, rồi lấy trung bình 4 yêu cầu hard)

**Bước 4 — Tính E_h (tỉ lệ yêu cầu hard có bằng chứng)**: trong 4 yêu cầu hard, có 3 yêu cầu ở trạng thái satisfied/partially_satisfied (Spring Boot, kinh nghiệm, cấp bậc), Java thì không → `E_h = 3/4 = 0.75`.

**Bước 5 — Tính S_align**: Y_align = min(6/5,1) = 1.0; L_align = 1.0 (Senior=Senior) → S_align = (1.0+1.0)/2 = 1.0.

**Bước 6 — C_s, E_s (cho yêu cầu soft = Docker)**: Docker là `not_satisfied` (điểm 0) → C_s = 0/3 = 0; E_s = 0/1 = 0.

**Bước 7 — B (độ giống nghĩa toàn văn bản)**: giả sử SBERT tính ra 0.62.

**Kết quả cuối — chuỗi 7 số của ứng viên này**:
```
K = (0, 0.83, 0.75, 1.0, 0, 0, 0.62)
```
Vì con số đầu tiên (`H_pass`) = 0, ứng viên này sẽ bị xếp **sau tất cả** những ứng viên có `H_pass` = 1, bất kể các con số phía sau (0.83, 0.75, 1.0...) đẹp đến đâu. Đây là minh họa cụ thể cho cơ chế "so sánh từ điển" ở Phần 3.2, và cũng là ví dụ cụ thể cho vấn đề mà luận văn tìm ra khi phân tích kết quả (Phần 6).

---

## Phần 6 — Vì sao kết quả cuối cùng "thua" cách làm cũ, và điều đó có ý nghĩa gì

### 6.1. Tóm tắt kết quả bằng một câu

Sau khi thử nghiệm trên 246 cặp CV-JD đã được con người chấm điểm đúng/sai bằng tay, hệ thống mới (RAEMatch) **xếp hạng kém chính xác hơn** so với việc chỉ dùng SBERT đơn giản (mục 1.4) để so sánh toàn văn bản.

Con số cụ thể (thang điểm NDCG@10, một cách đo "độ chính xác của thứ tự xếp hạng trong top 10", từ 0 đến 1, càng cao càng tốt — sẽ giải thích kỹ ở Phần 7):
- SBERT đơn giản: **0.96**
- Hệ thống đề xuất (RAEMatch): **0.64**

### 6.2. Tại sao lại như vậy? — Nguyên nhân đã tìm ra được chính xác

Giống hệt ví dụ tính tay ở Phần 5: rất nhiều ứng viên **thực sự phù hợp** vẫn bị `H_pass = 0` (fail gate) chỉ vì một chi tiết kỹ thuật rất cụ thể, không phải vì họ thực sự thiếu năng lực. Cụ thể:

Ngoài các yêu cầu về "kỹ năng" (Java, Docker...), JD còn có mục "Trách nhiệm công việc" (Key Responsibilities), ví dụ: *"Tham gia thiết kế hệ thống có khả năng mở rộng"*. Hệ thống coi **mọi câu trách nhiệm này đều là bắt buộc** (hard), và kiểm tra chúng bằng cách so sánh độ giống nghĩa với ngưỡng 0.55 — **giống hệt cách kiểm tra một từ khóa ngắn như "Java"**. Nhưng so sánh độ giống nghĩa của **cả một câu dài** thì khó đạt 0.55 hơn nhiều so với so sánh một từ ngắn, vì có rất nhiều cách diễn đạt khác nhau cho cùng một hoạt động.

Đã kiểm tra thực tế: trong số các ứng viên xếp hạng cao nhất, có người đạt đủ **100% các yêu cầu kỹ năng bắt buộc** nhưng vẫn bị đánh rớt `H_pass` chỉ vì đúng 1 câu "trách nhiệm công việc" bị chấm ở mức "đạt một phần" thay vì "đạt hoàn toàn". Thống kê trên toàn bộ 5 tin tuyển dụng dùng để test: **78% số lần bị đánh rớt yêu cầu bắt buộc là do câu trách nhiệm công việc này, chỉ 19% là do thực sự thiếu kỹ năng**.

Nói cách khác: lỗi không nằm ở *ý tưởng* "kiểm tra bằng chứng cụ thể" — mà nằm ở việc **áp dụng cùng một ngưỡng chấm điểm (0.55) cho hai loại nội dung có độ dài và cách diễn đạt rất khác nhau** (từ khóa ngắn vs. câu mô tả dài).

### 6.3. Vậy nghiên cứu này có "thất bại" không?

Không, vì **mục tiêu chính của luận văn không phải là "chính xác hơn SBERT"**, mà là xây dựng một hệ thống mà **mọi quyết định xếp hạng có thể giải thích được cho con người**. Ở điểm này, hệ thống làm được:

- SBERT chỉ cho ra một con số (ví dụ 0.62), không ai — kể cả người viết ra hệ thống — giải thích được vì sao ứng viên A được 0.62 còn ứng viên B được 0.58, ngoài "vector gần nhau hơn một chút".
- Hệ thống đề xuất, với mỗi ứng viên, luôn có thể trả lời chính xác: "yêu cầu Java: unsupported vì CV không có câu nào chứng minh; yêu cầu Spring Boot: satisfied nhờ câu 'Tôi đã xây dựng...'; kinh nghiệm: đạt (6/5 năm)...". Đây gọi là tính **auditable** (kiểm chứng được) hoặc **explainable** (giải thích được) — thứ SBERT không có, dù SBERT chính xác hơn.

Kiểm chứng thêm: trong số các kỹ năng mà hệ thống công nhận là "đạt" cho top 10 ứng viên, chỉ có **2.33%** là công nhận nhầm (không có bằng chứng thật) — nghĩa là 97.67% các lần công nhận đều có câu bằng chứng cụ thể đi kèm. Đây là bằng chứng cho thấy phần "kiểm tra bằng chứng" hoạt động đúng như thiết kế, độc lập với vấn đề ở mục 6.2.

### 6.4. Một hạn chế nhỏ khác đã biết: "khai láo vẫn có lợi một chút"

Nhớ lại thang điểm ở mục 2.3: `unsupported` = 1 điểm, `not_satisfied` = 0 điểm. Nghĩa là nếu ai đó **liệt kê khống** một kỹ năng không hề có bằng chứng, họ vẫn được nhiều điểm hơn người **không liệt kê gì cả** — dù ít điểm hơn nhiều so với người có bằng chứng thật (3 điểm). Đây là lý do "nhồi nhét từ khóa" (keyword stuffing) vẫn có lợi một phần dù hệ thống có cơ chế kiểm tra bằng chứng — một hạn chế thiết kế đã biết, chưa khắc phục hoàn toàn.

---

## Phần 7 — Các thước đo để chấm điểm "hệ thống xếp hạng tốt hay không"

Đây là phần dễ gây rối nhất nếu không có ví dụ cụ thể, nên mình sẽ tính tay từng bước.

### 7.0. Bối cảnh: "nhãn đúng" đến từ đâu?

Con người (1 người, gọi là "reviewer") đọc từng cặp (CV, JD) và chấm điểm mức độ phù hợp theo thang 0-3:
- 0 = Không phù hợp
- 1 = Phù hợp yếu
- 2 = Phù hợp
- 3 = Rất phù hợp

Đây gọi là **"nhãn thật"** (ground truth) — thứ duy nhất mà mọi thước đo bên dưới dùng để so sánh với thứ tự mà máy tính xếp ra.

### 7.1. Ví dụ xuyên suốt cho Phần 7

Giả sử máy tính xếp hạng ra thứ tự (từ hạng 1 đến hạng 5) cho 5 ứng viên, và nhãn thật con người đã chấm cho từng người là:

| Hạng máy xếp | Ứng viên | Nhãn thật (0-3) |
|---|---|---|
| 1 | An | 3 |
| 2 | Bình | 0 |
| 3 | Chi | 2 |
| 4 | Dũng | 0 |
| 5 | Em | 1 |

### 7.2. NDCG@k — "xếp đúng người giỏi lên đầu có tốt không"

**Ý tưởng bằng lời**: nếu người rất phù hợp (nhãn 3) được xếp hạng 1, đó là kết quả tuyệt vời. Nếu người rất phù hợp đó lại bị xếp hạng 5 (cuối bảng), đó là kết quả tệ dù "đúng" người đó có được liệt kê trong danh sách. NDCG (Normalized Discounted Cumulative Gain) đo chính xác điều này: **thưởng điểm cao nếu người tốt nằm ở đầu danh sách, phạt điểm nếu người tốt bị đẩy xuống cuối**.

**Công thức tính từng bước** (dùng đúng công thức trong code của luận văn):

Bước A — Tính điểm "gain" (lợi ích) của từng vị trí, dùng công thức `(2^nhãn - 1) / log2(vị trí + 2)`:

| Hạng (i, bắt đầu từ 0) | Nhãn | 2^nhãn - 1 | log2(i+2) | Gain = chia hai số trên |
|---|---|---|---|---|
| 0 (An) | 3 | 2³-1=7 | log2(2)=1.00 | 7/1.00 = 7.00 |
| 1 (Bình) | 0 | 2⁰-1=0 | log2(3)=1.58 | 0/1.58 = 0.00 |
| 2 (Chi) | 2 | 2²-1=3 | log2(4)=2.00 | 3/2.00 = 1.50 |
| 3 (Dũng) | 0 | 0 | log2(5)=2.32 | 0.00 |
| 4 (Em) | 1 | 2¹-1=1 | log2(6)=2.58 | 1/2.58 = 0.39 |

Cộng tất cả gain lại (gọi là **DCG** — Discounted Cumulative Gain): 7.00 + 0.00 + 1.50 + 0.00 + 0.39 = **8.89**

Bước B — Tính DCG "lý tưởng" (nếu xếp đúng thứ tự từ nhãn cao đến thấp: 3,2,1,0,0):

| Hạng lý tưởng | Nhãn | Gain |
|---|---|---|
| 0 | 3 | 7/1.00 = 7.00 |
| 1 | 2 | 3/1.58 = 1.89 |
| 2 | 1 | 1/2.00 = 0.50 |
| 3 | 0 | 0.00 |
| 4 | 0 | 0.00 |

Tổng DCG lý tưởng = 7.00+1.89+0.50 = **9.39**

Bước C — **NDCG = DCG thực tế ÷ DCG lý tưởng** = 8.89 / 9.39 = **0.947**

**Đọc kết quả**: 0.947 rất gần 1.0, nghĩa là thứ tự máy xếp gần như tối ưu — dù Bình (nhãn 0) bị xếp hạng 2 (hơi phí vị trí đẹp), nhưng vì An (nhãn 3, tốt nhất) vẫn đứng đầu nên điểm phạt không quá nặng. **NDCG@10** trong luận văn nghĩa là chỉ tính công thức này cho 10 vị trí đầu tiên (nếu danh sách dài hơn 10, phần sau bị cắt bỏ, không tính).

### 7.3. MAP — "trung bình độ chính xác tại mỗi lần gặp người phù hợp"

**Quy ước**: một người được coi là "phù hợp" (relevant) nếu nhãn ≥ 2 (tức nhãn 2 hoặc 3). Với ví dụ ở Phần 7.1: An (nhãn 3) và Chi (nhãn 2) là "phù hợp"; Bình, Dũng, Em thì không.

**Cách tính Average Precision (AP) — bằng lời**: đi từ hạng 1 xuống hạng cuối, mỗi khi gặp một người "phù hợp", tính xem "trong số người đã xem tính đến giờ, bao nhiêu % là phù hợp", rồi lấy trung bình các con số đó.

| Hạng | Ứng viên | Phù hợp? | Số người phù hợp đã gặp | Precision tại vị trí này |
|---|---|---|---|---|
| 1 | An | Có | 1 | 1/1 = 1.00 |
| 2 | Bình | Không | — | (không tính) |
| 3 | Chi | Có | 2 | 2/3 = 0.67 |
| 4 | Dũng | Không | — | (không tính) |
| 5 | Em | Không | — | (không tính) |

AP = trung bình của các con số đã tính (1.00 và 0.67) = (1.00+0.67)/2 = **0.835**

**MAP** (Mean Average Precision) = lấy AP tính như trên cho **từng JD riêng biệt**, rồi lấy trung bình cộng qua tất cả JD (luận văn có 5 JD, nên MAP = trung bình của 5 con số AP).

### 7.4. MRR — "người phù hợp đầu tiên xuất hiện nhanh cỡ nào"

**Ý tưởng bằng lời**: chỉ quan tâm **người phù hợp đầu tiên** xuất hiện ở hạng thứ mấy, không quan tâm phần còn lại của danh sách ra sao.

Công thức: MRR = 1 / (hạng của người phù hợp đầu tiên). Ví dụ ở Phần 7.1: người phù hợp đầu tiên là An, ở hạng 1 → MRR = 1/1 = **1.0** (điểm tuyệt đối vì người tốt nằm ngay đầu).

Nếu người phù hợp đầu tiên nằm ở hạng 3 thay vì hạng 1 → MRR = 1/3 = 0.33 (thấp hơn nhiều, dù phần còn lại của danh sách có thể vẫn ổn).

**Vì sao MRR của hệ thống đề xuất "cao bất thường" (0.90) dù các chỉ số khác thấp?** Vì MRR chỉ nhìn vào người đầu tiên — hệ thống đề xuất vẫn khá giỏi đưa **một người tốt** lên đầu (nhờ cơ chế ưu tiên "ai đạt hết yêu cầu bắt buộc" ở Phần 3, khi nó thực sự hoạt động đúng), nhưng không giỏi bằng trong việc xếp *toàn bộ* top 10-20 người cho thật chuẩn — đó là lý do NDCG/Recall (nhìn toàn bộ danh sách) thấp hơn nhiều so với MRR (chỉ nhìn 1 người).

### 7.5. Recall@k — "trong số người phù hợp thật sự có bao nhiêu người lọt vào top-k"

Ví dụ: giả sử trong toàn bộ danh sách ứng viên (không chỉ 5 người ở ví dụ trên) có tổng cộng 10 người "phù hợp" (nhãn ≥ 2) theo đánh giá con người. Máy tính xếp hạng ra top 10, trong đó có 4 người thuộc nhóm 10 người phù hợp kể trên.

```
Recall@10 = 4 / 10 = 0.4
```

Nghĩa là máy tính chỉ "bắt được" 40% số ứng viên thật sự phù hợp trong top 10 — 60% còn lại bị lọt ra ngoài top 10 dù họ xứng đáng có mặt ở đó.

### 7.6. Vì sao gọi là "macro-average"?

Luận văn có 5 JD khác nhau, mỗi JD có 46-50 cặp CV đã chấm nhãn. **Macro-average** nghĩa là: tính riêng NDCG (hoặc MAP, MRR, Recall) cho từng JD, rồi lấy **trung bình cộng đơn giản của 5 con số đó** — JD có 46 cặp và JD có 50 cặp được coi trọng như nhau, không ưu tiên JD nào có nhiều dữ liệu hơn. Mục đích: tránh 1 JD có nhiều CV át hết kết quả của các JD còn lại.

---

## Phần 8 — Sáu "phiên bản" mô hình được so sánh (M1 đến M6)

Luận văn không chỉ có 1 hệ thống — nó so sánh **6 cách làm khác nhau** trên cùng một bộ dữ liệu, để biết chính xác từng "mảnh" ý tưởng đóng góp bao nhiêu:

| Tên | Cách hoạt động (giải thích bằng lời) |
|---|---|
| **M1 — TF-IDF** | Đếm từ khóa (Phần 1.3). Baseline cũ nhất, đơn giản nhất. |
| **M2 — SBERT full text** | So sánh toàn bộ văn bản CV với toàn bộ văn bản JD bằng embedding (Phần 1.4). Đây là baseline mạnh nhất trong thực nghiệm. |
| **M3 — Section-level SBERT** | Giống M2 nhưng tách CV thành từng phần (Skills, Kinh nghiệm, Học vấn), tính SBERT riêng cho từng phần rồi lấy trung bình — hy vọng giảm nhiễu từ những đoạn văn không liên quan trong CV dài. |
| **M4 — Requirement-aware** | Bắt đầu áp dụng ý tưởng "tách yêu cầu" (Phần 2.1), nhưng **chưa kiểm tra bằng chứng** — chỉ xem yêu cầu có được liệt kê trong Skills hay xuất hiện ở đâu đó trong CV hay không (giống/khác với "khai láo" đều được tính là có). |
| **M5 — Requirement + seniority** | Giống M4 về cách kiểm tra (chưa có bằng chứng), nhưng bắt đầu dùng cơ chế xếp hạng "từ điển" đầy đủ ở Phần 3 (có `H_pass` gate). |
| **M6 — Full proposed model** | Phiên bản đầy đủ nhất: tách yêu cầu + kiểm tra bằng chứng thật (Phần 2.2) + xếp hạng từ điển (Phần 3). Đây là hệ thống chính luận văn đề xuất. |

**Vì sao cần cả 6 phiên bản, không chỉ M6?** Để trả lời câu hỏi "mỗi ý tưởng thêm vào có thực sự giúp ích hay không" — đây gọi là **ablation study** (thử nghiệm loại bỏ từng phần). Kết quả cho thấy: M4 (0.39 NDCG@10) < M5 (0.55) < M6 (0.64) — nghĩa là thêm cơ chế gate (M4→M5) và thêm kiểm tra bằng chứng (M5→M6) **đều thực sự giúp ích**, đúng như kỳ vọng thiết kế. Vấn đề chỉ là cả ba vẫn thấp hơn M1/M2/M3 — lý do đã giải thích ở Phần 6.2.

---

## Phần 9 — Ứng dụng (app) hoạt động ra sao ở tầng kỹ thuật

Phần này dành cho khi hội đồng hỏi về mặt triển khai phần mềm, không phải thuật toán.

### 9.1. Ứng dụng gồm 2 phần

- **Backend** (phần xử lý dữ liệu, "bộ não"): viết bằng Python, dùng framework FastAPI để tạo các "cửa" (API) cho phép frontend gửi yêu cầu (VD: "xếp hạng CV cho JD này giúp tôi") và nhận kết quả về.
- **Frontend** (giao diện người dùng): viết bằng React (một thư viện JavaScript phổ biến để làm giao diện web), là thứ nhà tuyển dụng thực sự nhìn thấy và bấm chuột vào.

### 9.2. Dữ liệu được lưu ở đâu?

Trong một file cơ sở dữ liệu (SQLite — một loại database gọn nhẹ, lưu trong 1 file duy nhất, không cần cài server riêng), gồm 3 "bảng":
- Bảng `cvs`: lưu thông tin từng CV (văn bản gốc, văn bản đã làm sạch, danh sách kỹ năng trích ra được, số năm kinh nghiệm, cấp bậc...).
- Bảng `job_descriptions`: lưu thông tin từng JD (tiêu đề, mô tả, danh sách yêu cầu đã tách — chính là kết quả của Phần 2.1).
- Bảng `reviewer_labels`: lưu nhãn 0-3 mà con người đã chấm cho từng cặp CV-JD (dùng để tính các thước đo ở Phần 7).

### 9.3. Khi upload một CV (file PDF), điều gì xảy ra?

1. Thử trích xuất chữ trực tiếp từ file PDF (nhanh, chính xác — áp dụng cho PDF có "lớp chữ" thật bên trong, không phải ảnh scan).
2. Nếu bước 1 không ra được chữ (vì file chỉ là ảnh scan) → chuyển sang **OCR** (Optical Character Recognition — công nghệ "đọc chữ từ ảnh"), dùng công cụ mã nguồn mở tên **Tesseract**: chụp từng trang PDF thành ảnh, rồi Tesseract "nhìn" ảnh đó và đoán ra từng chữ cái.
3. Với văn bản đã có (dù từ bước 1 hay 2), hệ thống tìm các "tiêu đề mục" quen thuộc (Skills, Work Experience, Education...) để tách CV thành từng phần.
4. Trích ra danh sách kỹ năng (so khớp với một từ điển kỹ năng công nghệ đã chuẩn bị sẵn), số năm kinh nghiệm (tìm cụm từ kiểu "5 years of experience" hoặc tính từ khoảng ngày làm việc), và cấp bậc (tìm từ khóa như "Senior", "Junior"...).

### 9.4. Khi tạo một JD, điều gì xảy ra?

Tương tự bước 3-4 ở trên nhưng áp dụng cho JD: tìm tiêu đề mục như "Mandatory Requirements" (bắt buộc), "Preferred / Optional Skills" (tùy chọn), "Key Responsibilities" (trách nhiệm), rồi trích ra danh sách yêu cầu, gán nhãn hard/soft dựa vào JD ghi kỹ năng đó dưới mục nào (đây chính là bước "requirement decomposition" ở Phần 2.1, được lập trình bằng luật cố định — gọi là **rule-based**, nghĩa là dùng quy tắc do con người viết sẵn, không phải AI tự học).

**Lưu ý kỹ thuật quan trọng**: nếu JD không dùng đúng cụm từ tiêu đề mà hệ thống đã được lập trình để nhận diện, nó sẽ **không tách được** mandatory/optional, và mặc định coi **toàn bộ kỹ năng tìm thấy trong JD đều là bắt buộc** — đây từng là một lỗi cụ thể được phát hiện và sửa trong quá trình làm luận văn (mở rộng danh sách các cụm từ tiêu đề mà hệ thống nhận diện được).

### 9.5. Khi bấm "Xếp hạng" (Rank), điều gì xảy ra?

1. Lấy toàn bộ CV đã lưu trong hệ thống (ví dụ 3,986 CV).
2. Với mỗi CV, tính embedding (Phần 1.1) cho: toàn văn bản, từng phần (Skills/Experience/Education), và từng câu trong phần Kinh nghiệm/Dự án (để dùng làm "câu bằng chứng" ở Phần 2.2). Việc này **chỉ làm 1 lần** cho mỗi CV rồi lưu lại trong bộ nhớ máy tính (gọi là **cache** — "bộ nhớ đệm", để lần sau dùng lại không phải tính lại từ đầu) — đây là lý do lần xếp hạng đầu tiên chậm (~200 giây cho 3,986 CV) nhưng các lần xếp hạng JD khác sau đó nhanh hơn nhiều (~10-20 giây).
3. Chọn 1 trong 6 cách làm (M1-M6, Phần 8) để tính điểm/chuỗi xếp hạng cho từng CV.
4. Sắp xếp toàn bộ CV theo điểm/chuỗi đó, trả về top-k CV đầu bảng (ví dụ top 10) kèm theo lời giải thích chi tiết cho từng CV (yêu cầu nào đạt/không đạt, câu bằng chứng nào được dùng) — đây chính là phần **"explanation"** hiển thị cho nhà tuyển dụng.

### 9.6. Con người tham gia ở đâu? ("Human-in-the-loop")

Hệ thống **không tự động loại** ứng viên nào. Nó chỉ đưa ra danh sách đã xếp hạng + giải thích. Nhà tuyển dụng (gọi là "reviewer" trong luận văn) xem danh sách này, có thể tự chấm nhãn phù hợp/không phù hợp (0-3) để lưu lại — nhãn này được dùng để tính các thước đo ở Phần 7. Quyết định tuyển hay không tuyển luôn do con người quyết định cuối cùng.

---

## Phần 10 — Bảng thuật ngữ tra nhanh (glossary)

| Thuật ngữ | Giải thích ngắn gọn |
|---|---|
| CV / JD | Hồ sơ ứng viên / Tin tuyển dụng (mô tả công việc) |
| Embedding | Một dãy số (384 số trong luận văn này) đại diện cho ý nghĩa của một đoạn văn |
| Cosine similarity | Con số từ 0 đến 1 đo "hai đoạn văn giống nghĩa nhau đến đâu" |
| TF-IDF | Cách so khớp bằng đếm từ khóa (không hiểu nghĩa) |
| SBERT | Mô hình AI biến câu văn thành embedding rồi so bằng cosine similarity (hiểu nghĩa) |
| Requirement decomposition | Tách JD thành từng yêu cầu riêng lẻ thay vì coi là 1 đoạn văn |
| Hard / Soft requirement | Yêu cầu bắt buộc / Yêu cầu tùy chọn (có thì cộng điểm) |
| Evidence-aware matching | Kiểm tra CV có câu văn cụ thể chứng minh kỹ năng, không chỉ tin việc liệt kê |
| Declared | Kỹ năng được liệt kê trong mục Skills của CV |
| Evidenced | Kỹ năng có câu bằng chứng cụ thể trong phần Kinh nghiệm/Dự án |
| Threshold (ngưỡng) τ_l, τ_h | Ranh giới cosine similarity để phân loại 4 trạng thái (0.35 và 0.55) |
| H_pass | Có đạt hết mọi yêu cầu bắt buộc hay không (1 = có, 0 = không) |
| Lexicographic ranking key | Cách xếp hạng so sánh nhiều tiêu chí theo thứ tự ưu tiên tuyệt đối, giống sắp xếp từ điển |
| Baseline | Phương pháp có sẵn dùng để so sánh với phương pháp mới đề xuất |
| Ranking | Xếp hạng — sắp xếp danh sách theo thứ tự phù hợp giảm dần |
| NDCG@k | Thước đo: người phù hợp có được xếp lên đầu top-k hay không (0-1, càng cao càng tốt) |
| MAP | Trung bình độ chính xác tại mỗi lần gặp người phù hợp |
| MRR | Người phù hợp đầu tiên xuất hiện ở hạng thứ mấy (1/hạng đó) |
| Recall@k | Bao nhiêu % người phù hợp thật sự lọt được vào top-k |
| Macro-average | Trung bình cộng đơn giản qua các JD, không ưu tiên JD nào có nhiều dữ liệu hơn |
| Ablation study | Thử bỏ/thêm từng phần cơ chế để xem phần nào thực sự có ích (đây là M1-M6) |
| OCR | Công nghệ đọc chữ từ ảnh scan (dùng Tesseract trong luận văn) |
| Rule-based | Lập trình bằng quy tắc cố định do con người viết, không phải AI tự học |
| Human-in-the-loop | Con người luôn là người ra quyết định cuối cùng, máy chỉ hỗ trợ |
| Auditable / Explainable | Có thể giải thích rõ ràng vì sao ra kết quả đó, không phải "hộp đen" |
| Bootstrap CI | Cách ước lượng độ tin cậy của một con số bằng cách lấy mẫu lại (resampling) nhiều lần |
| Reviewer | Người chấm nhãn 0-3 cho từng cặp CV-JD, dùng làm "đáp án đúng" để so sánh |
