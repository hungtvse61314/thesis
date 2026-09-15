# RAEMatch — Câu hỏi hội đồng dự kiến và câu trả lời

> Sắp xếp theo nhóm chủ đề, từ dễ đến "khó/nhạy cảm nhất". Mỗi câu trả lời viết theo hướng: thừa nhận thẳng nếu là hạn chế thật, rồi giải thích lý do/hướng khắc phục — tránh vòng vo hoặc chống chế, vì bản thân luận văn đã chọn phong cách trung thực báo cáo cả kết quả bất lợi.

---

## A. Nhóm câu hỏi về động lực & phạm vi

**Q1. Vì sao chọn hướng requirement-aware/evidence-aware thay vì chỉ fine-tune một model similarity tốt hơn?**

> Fine-tune một model similarity tốt hơn (ví dụ cross-encoder) có thể tăng accuracy, nhưng vẫn trả về **một con số duy nhất** không giải thích được — nhà tuyển dụng không biết ứng viên thiếu cụ thể điều gì. Mục tiêu của luận văn không phải tối đa hóa accuracy bằng mọi giá, mà là xây dựng cơ chế mà **mỗi quyết định xếp hạng truy vết được về một requirement, một ngưỡng, một câu bằng chứng cụ thể** — điều mà similarity thuần túy không cấu trúc để làm được, dù có mạnh đến đâu.

**Q2. Tại sao chỉ giới hạn ở IT recruitment, tiếng Anh?**

> Vì domain IT có từ vựng kỹ thuật tương đối chuẩn hóa (tên công nghệ, framework) giúp việc trích xuất skill và xây dựng dictionary khả thi trong phạm vi luận văn thạc sĩ. Mở rộng đa ngành/đa ngôn ngữ đòi hỏi dictionary và luật phân tích khác hẳn, được liệt kê rõ trong Scope and Exclusions (Chương 1) và Future Work (Chương 5) như hướng mở rộng, không phải giới hạn bị bỏ sót.

**Q3. Hệ thống có thay thế được recruiter không?**

> Không, và đây là chủ đích thiết kế, không phải hạn chế. Hệ thống chỉ ưu tiên thứ tự xem xét (review priority) và cung cấp giải thích; quyết định tuyển dụng cuối cùng luôn thuộc về con người (Chương 3, Human-in-the-loop). Điều này còn được nhấn mạnh vì hệ thống hiện **chưa che (mask) thông tin cá nhân** trước khi hiển thị cho reviewer — một hạn chế đã ghi rõ trong Limitations.

---

## B. Nhóm câu hỏi về thiết kế & công thức

**Q4. Vì sao dùng lexicographic ranking key thay vì cộng có trọng số (weighted sum)?**

> Vì weighted sum cho phép **bù trừ** — similarity toàn văn bản cao có thể che lấp việc thiếu một requirement bắt buộc. Lexicographic key `K(d,q) = (H_pass, C_h, E_h, S_align, C_s, E_s, B)` so sánh từng thành phần theo thứ tự ưu tiên tuyệt đối: ứng viên đạt `H_pass=1` luôn đứng trước ứng viên `H_pass=0`, bất kể điểm similarity B chênh lệch bao nhiêu. Đánh đổi là hệ thống trở nên "cứng" hơn — chỉ cần fail 1 constraint cứng là bị đẩy xuống rất xa, kể cả khi các mặt khác rất tốt. Đây chính xác là điều đang xảy ra với responsibility items (xem Q13).

**Q5. Ngưỡng τ_l=0.35, τ_h=0.55 lấy từ đâu? Có cơ sở khoa học không?**

> Đây là giá trị mặc định của prototype, **được thừa nhận thẳng là chưa calibrate** trên dữ liệu (Chương 3, Chương 4). Thí nghiệm threshold-sensitivity và held-out calibration (Table threshold-sensitivity, threshold-calibration) cho thấy ngưỡng chặt hơn (0.50/0.70) cho kết quả tốt hơn ~52% relative trên NDCG@10 — nghĩa là mặc định hiện tại hơi lỏng, không phải quá chặt như giả thuyết ban đầu. Đây là một phát hiện thực nghiệm quan trọng của luận văn, không phải một điểm yếu bị giấu.

**Q6. Trọng số w_j trong r_j=(t_j,c_j,w_j) dùng để làm gì? Có thực sự được dùng không?**

> Về mặt thiết kế, w_j đại diện cho mức độ quan trọng riêng của từng requirement bên trong nhóm hard/soft. Trong triển khai hiện tại, w_j luôn = 1.0 — tức mọi requirement cùng loại (hard hoặc soft) được coi trọng như nhau. Đây là điểm có thể cải tiến (dùng w_j để phân biệt "phải có Java" quan trọng hơn "phải có Git" trong cùng nhóm hard), nhưng chưa được khai thác trong thực nghiệm này.

**Q7. Tại sao Recall@10/20 lại thấp hơn hẳn so với NDCG, đặc biệt ở M4-M6?**

> Vì recall đo tỉ lệ ứng viên relevant (label≥2) **thực sự nằm trong top-k**, trong khi cơ chế constraint-based reranking có thể đẩy một ứng viên relevant (theo đánh giá con người) xuống dưới top-10/20 chỉ vì fail một requirement mà bản thân requirement đó bị phân loại/đánh giá chưa chuẩn (ví dụ responsibility). Đây chính là biểu hiện định lượng của vấn đề gate quá khắt khe đã nêu ở Q13.

---

## C. Nhóm câu hỏi về thiết kế thực nghiệm

**Q8. Vì sao chỉ có 1 reviewer gán nhãn? Điều này có làm mất giá trị kết luận không?**

> Đây là hạn chế thật, được liệt kê tường minh trong Threats to Validity (Construct Validity) và Limitations. Không tính được Cohen's kappa vì cần ≥2 reviewer. Rubric 5 tiêu chí có trọng số (mandatory skill 30%, experience 25%...) được dùng để giảm tính chủ quan, nhưng không thay thế được việc có người thứ hai đối chiếu. Đây là mục đầu tiên trong "Immediate next steps" của Future Work.

**Q9. Vì sao trộn CV thật và CV synthetic trong cùng 1 pool đánh giá chính (246 cặp), thay vì tách riêng?**

> Vì mục tiêu ban đầu là dùng synthetic CV chỉ cho robustness/scalability test, còn 246-pair pool nên là toàn bộ CV thật. Nhưng khi pooling ứng viên để gán nhãn (lấy top-k từ cả 6 model + mẫu ngẫu nhiên), một phần synthetic CV lọt vào pool này (43.9%, tức 108/246 cặp). Đây được báo cáo rõ là **một sai lệch so với thiết kế ban đầu**, không phải cố ý, và liệt kê là limitation: không tách được ảnh hưởng của synthetic CV lên kết quả chính vì không làm breakdown real-only/synthetic-only riêng.

**Q10. Vì sao dùng bootstrap CI + Wilcoxon mà Wilcoxon không bao giờ có ý nghĩa thống kê (p<0.05)?**

> Với chỉ n=5 JD, phép kiểm định Wilcoxon signed-rank hai phía có **giá trị p nhỏ nhất về mặt toán học là 1/16 = 0.0625** — không thể nhỏ hơn 0.05 dù hiệu ứng lớn cỡ nào, vì đây là giới hạn rời rạc của phân phối kiểm định với cỡ mẫu này, không phải do kết quả yếu. Bootstrap CI (dùng resampling 5 JD với B=10,000 lần) cho thấy khoảng tin cậy 95% của hiệu số so với M6 loại trừ 0 đối với cả 3 baseline similarity-only — đây là bằng chứng thuyết phục hơn Wilcoxon ở cỡ mẫu này, và cả hai được báo cáo song song thay vì chỉ chọn phép kiểm định "đẹp".

**Q11. 5 JD có đủ đại diện không? Tại sao không nhiều hơn?**

> 5 JD được chọn có chủ đích bao phủ đa dạng: 2 mức seniority khác nhau trên cùng stack (Senior/Junior Java), 3 domain khác nhau (Java, React, .NET) và 1 role kiến trúc cấp cao (Solution Architect, 8 năm). Đây là giới hạn về thời gian/nguồn lực của luận văn thạc sĩ, được thừa nhận trong Conclusion Validity, và per-JD breakdown (Table per-jd-ndcg10) cho thấy kết luận chính không phụ thuộc vào 1 JD cụ thể nào chi phối trung bình.

---

## D. Nhóm câu hỏi về kết quả (khó nhất — chuẩn bị kỹ)

**Q12. Câu hỏi trực diện nhất: Nếu SBERT thuần túy thắng mô hình đề xuất trên hầu hết mọi metric, đóng góp thực sự của luận văn là gì?**

> Đóng góp không nằm ở accuracy mà ở **tính minh bạch (auditability)**. SBERT trả về một điểm cosine duy nhất — không ai, kể cả người phát triển, giải thích được vì sao ứng viên A xếp trên ứng viên B ngoài "vector gần nhau hơn". Mô hình đề xuất (M6) với top-10 ứng viên của nó có **unsupported-claim rate chỉ 2.33%** — nghĩa là gần như mọi skill được công nhận đều có câu bằng chứng cụ thể kèm theo, và mọi case-study trong Chương 4 đều chỉ ra được chính xác requirement nào đạt, requirement nào thiếu, ngưỡng so sánh là bao nhiêu. Đây là một thuộc tính SBERT không thể có về mặt cấu trúc, bất kể accuracy của nó cao đến đâu. Luận văn không tuyên bố "accuracy tốt hơn" — nó tuyên bố và chứng minh được "minh bạch hơn, với một chi phí accuracy đã đo lường được cụ thể".

**Q13. Vì sao constraint violation rate@10 lại là 100% cho cả M5 và M6 trên cả 5 JD — nghĩa là cơ chế gating hoàn toàn không hoạt động?**

> Đã xác định chính xác nguyên nhân bằng cách kiểm tra trực tiếp assessment của các ứng viên xếp hạng cao nhất: **các câu "Key Responsibilities" luôn bị gán là hard requirement một cách vô điều kiện** (bất kể JD có phân loại rõ mandatory/optional hay không), và được đánh giá bằng chính ngưỡng similarity 0.55 vốn được thiết kế cho so khớp skill ngắn. Một câu mệnh lệnh dài (ví dụ "Participate in the design of scalable, maintainable, and reliable software architectures") rất khó đạt cosine similarity ≥0.55 với một câu CV viết khác cách diễn đạt, dù mô tả đúng hoạt động đó. Kiểm chứng định lượng: top-3 ứng viên của EVAL_JD_01 đạt cả 5/5 skill bắt buộc nhưng vẫn fail gate vì đúng 1 câu responsibility rơi vào `partially_satisfied`. Tổng hợp trên cả 5 JD: **78% số lượt fail hard-requirement ở top-10 là do responsibility, chỉ 19% do skill thật sự thiếu**. Đây là nguyên nhân đã xác định chính xác, được đưa vào Future Work như bước sửa cụ thể tiếp theo (đưa responsibility về soft, hoặc dùng ngưỡng riêng thấp hơn cho câu dài).

**Q14. Trong quá trình đánh giá, các anh có phát hiện và sửa lỗi nào trong hệ thống không? Nếu có, tại sao không nói rõ trong luận văn?**

> Có. Trong quá trình phân tích tại sao `H_pass` không bao giờ đúng, chúng tôi phát hiện và sửa một lỗi cụ thể trong bộ dò heading của JD parser (`jd_parsing.py`): heading "Mandatory Requirements" và "Preferred / Optional Skills" — đúng cách các JD đánh giá được soạn — không khớp với danh sách từ đồng nghĩa mà parser cấu hình sẵn (vốn chỉ nhận "required skills", "preferred skills"...). Đã mở rộng danh sách này, chạy lại toàn bộ 246 cặp, và **số liệu trong Table 4.1 hiện tại là kết quả sau khi sửa** — đây chính là "kết quả cuối cùng" được báo cáo trong luận văn, không phải kết quả tạm thời. Chúng tôi chọn trình bày trực tiếp trạng thái cuối cùng của hệ thống thay vì kể lại toàn bộ quá trình debug, vì báo cáo mô tả hệ thống *đã hoàn thiện*, không phải nhật ký phát triển. Nếu hội đồng muốn biết chi tiết kỹ thuật của việc sửa lỗi này, có thể trình bày thêm (xem code diff trong `backend/app/services/jd_parsing.py`).
>
> *(Lưu ý riêng cho anh: câu trả lời này giả định hội đồng hỏi thẳng — nếu không ai hỏi, không cần chủ động kể chi tiết quá trình debug, vì bản in hiện tại đã chọn cách trình bày "kết quả cuối" theo đúng quyết định anh đưa ra.)*

**Q15. Tại sao Requirement-aware (M4) — bước đầu tiên của "cơ chế đề xuất" — lại tệ hơn cả Section-level SBERT (M3), một baseline đơn giản hơn nhiều?**

> Vì M4 dùng cơ chế đánh giá "declared-only" — chỉ kiểm tra một skill có được liệt kê trong CV hay không (đúng/sai nhị phân), bỏ hoàn toàn thông tin ngữ nghĩa liên tục mà SBERT tận dụng (từ đồng nghĩa công nghệ, cách diễn đạt khác nhau cho cùng một kỹ năng). Việc "rời rạc hóa" requirement giúp minh bạch hơn (biết chính xác skill nào đạt) nhưng trả giá bằng việc mất đi sự linh hoạt ngữ nghĩa. M5 và M6 lần lượt bù lại một phần bằng cách thêm seniority constraint và evidence verification thực sự — đây chính là lý do pattern M4 < M5 < M6 tăng dần đúng như thiết kế, dù cả ba đều chưa vượt qua baseline similarity-only.

**Q16. Kết quả robustness cho thấy role-confusion chỉ đúng 1/3 trường hợp — đây có phải lỗi nghiêm trọng của hệ thống không?**

> Đây là điểm yếu thật và là phát hiện có giá trị của việc mở rộng battery test từ 1 lên 3 instance (nếu chỉ dừng ở 1 instance ban đầu, kết luận sẽ là "hệ thống xử lý tốt role confusion" — một kết luận sai). Nguyên nhân: việc trích xuất skill hiện quét toàn bộ text CV, không giới hạn theo ngữ cảnh cá nhân — một Business Analyst hoặc QA Tester mô tả dự án bằng cụm từ như "a Python-based data pipeline" vẫn bị tính là có bằng chứng cho skill Python, dù đó là mô tả dự án chứ không phải kỹ năng cá nhân của họ. Đây là hạn chế cụ thể, đã định vị chính xác nguyên nhân, và là mục thứ hai trong Immediate Next Steps: giới hạn phạm vi trích skill vào các câu có chủ ngữ ngôi thứ nhất/sở hữu cách, thay vì quét toàn văn bản.

**Q17. Tại sao MRR của M6 (0.9000) lại gần bằng baseline trong khi các metric khác thua xa?**

> MRR chỉ đo vị trí của ứng viên relevant **đầu tiên** xuất hiện, không quan tâm đến toàn bộ chất lượng xếp hạng phía sau. M6 vẫn khá giỏi trong việc đưa *một* ứng viên tốt lên đầu danh sách (nhờ cơ chế gate ưu tiên constraint cứng khi nó thực sự pass), nhưng không giỏi bằng trong việc duy trì chất lượng xếp hạng ổn định trên toàn bộ top-10/20 — đây là lý do NDCG và Recall (đo toàn bộ danh sách) thấp hơn nhiều so với MRR.

---

## E. Nhóm câu hỏi triển khai/kỹ thuật

**Q18. Vì sao chọn all-MiniLM-L6-v2 mà không phải model SBERT lớn hơn?**

> Đây là mô hình nhỏ (384 chiều), tốc độ nhanh, chạy tốt trên CPU không cần GPU — phù hợp với mục tiêu prototype có thể demo được trên máy cá nhân, đồng thời đủ mạnh để làm baseline SBERT cạnh tranh (thực tế nó vẫn thắng cơ chế đề xuất). Mô hình lớn hơn có thể cải thiện cả baseline lẫn evidence retrieval, nhưng đánh đổi là latency — đã đo: index build ~203s cho 3,986 CV, ranking mỗi JD ~10-20s với model hiện tại.

**Q19. Tại sao M4/M5 (declared-only, tưởng chừng đơn giản hơn) lại tốn thời gian ranking nhiều hơn M6 (evidence-aware, có vẻ phức tạp hơn)?**

> Vì M4/M5 dùng regex/text-search trên toàn bộ văn bản CV cho từng cặp (requirement, CV) trong mỗi lần gọi — không có cache. M6 dùng embedding đã được cache sẵn từ trước (tính 1 lần khi index), nên chỉ cần một phép nhân ma trận (cosine similarity vector hóa) rất nhanh. Đây là một phát hiện phản trực giác nhưng đã đo đạc cụ thể: M4/M5 tốn 14.8-21.5s/JD, M6 chỉ 10.8-15.1s/JD trên cùng corpus 3,986 CV.

**Q20. OCR success rate 100% có đáng tin không?**

> Con số này **có tính tautological (đúng theo định nghĩa)** và được nói rõ trong luận văn: nó chỉ tính trên các file *đã được index thành công* — file OCR thất bại không bao giờ vào được mẫu số này vì bị loại ngay từ đầu, không phải vì mọi lần upload đều thành công. Tỉ lệ thất bại thật (trên tổng số file từng thử upload) hiện không thể khôi phục vì hệ thống ban đầu không log các lần upload thất bại — đây là một limitation đã ghi rõ, không phải một tuyên bố ẩn ý gây hiểu lầm.

**Q21. Dữ liệu và mô hình có được bảo mật không? Có gửi CV ra ngoài (OpenAI, cloud...) không?**

> Không. OCR (Tesseract) và embedding (sentence-transformers) đều chạy hoàn toàn local, không gọi API bên ngoài trong lúc vận hành. Tuy nhiên, dữ liệu synthetic CV (1,000 CV) được **sinh ra** bằng ChatGPT ở giai đoạn chuẩn bị dữ liệu (một lần, ngoài luồng vận hành), khác với việc gửi CV thật của ứng viên đi xử lý. Về bảo mật khi vận hành: tên, email, số điện thoại **chưa được che** trước khi hiển thị cho reviewer — đây là hạn chế đã nêu rõ, cần làm trước khi triển khai thực tế.

---

## F. Câu hỏi tổng hợp/triết lý (thường hỏi cuối buổi)

**Q22. Nếu làm lại từ đầu, anh sẽ thay đổi thiết kế nào?**

> Gợi ý trả lời: (1) Không dùng lexicographic key "tất cả hoặc không" cho mọi requirement hard như nhau — nên phân biệt rõ responsibility (câu dài, mô tả hoạt động) khỏi skill (từ khóa ngắn) ngay từ đầu, dùng ngưỡng và cơ chế đánh giá khác nhau cho hai loại. (2) Calibrate ngưỡng τ trên tập dev **trước khi** chạy đánh giá chính, không phải sau. (3) Tuyển 2 reviewer ngay từ đầu thay vì phát hiện thiếu ở cuối.

**Q23. Nghiên cứu này có thể ứng dụng thực tế ngay không, hay chỉ dừng ở mức prototype học thuật?**

> Dừng ở mức prototype có kiểm chứng (validated prototype), chưa sẵn sàng triển khai thực tế. Ba rào cản cụ thể trước khi triển khai: (1) chưa che thông tin cá nhân (PII masking), (2) constraint gate cần sửa để không loại nhầm ứng viên tốt vì lỗi phân loại responsibility, (3) chỉ kiểm chứng trên 5 JD/246 cặp — cần validate trên dữ liệu doanh nghiệp thật với quy mô lớn hơn trước khi tin tưởng đưa vào quy trình tuyển dụng thật.

**Q24. Câu hỏi bẫy: Vậy cuối cùng RQ1 có được trả lời "có" hay "không"?**

> Trả lời thẳng: **Không** — với dữ liệu và cấu hình hiện tại, requirement-aware/evidence-aware matching **không** cải thiện chất lượng xếp hạng so với similarity-only trên tập 246 cặp đã gán nhãn (NDCG@10 0.64 so với 0.96 của SBERT). Đây không phải một câu trả lời né tránh — luận văn xác định được chính xác nguyên nhân (responsibility hard-gating quá khắt khe) và định vị đây là vấn đề kỹ thuật cụ thể có thể sửa, không phải bằng chứng cho thấy hướng tiếp cận requirement-decomposition là sai về nguyên tắc. RQ2 (giảm false-positive qua constraint/evidence) thì được trả lời "có" ở mức đáng tin cậy cho 3/4 loại lỗi kiểm tra.
