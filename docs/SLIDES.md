# SLIDES: DATA PIPELINE & DATA OBSERVABILITY FOR RAG SYSTEMS
**Khóa học / Bài Lab:** K4-L3B-DAY10  
**Tên Nhóm:** `Latentia`  
**Thành viên:**  
1. Nguyễn Minh Tuấn (2A202602420) - Techlead & Pipeline Integrator  
2. Nguyễn Minh Thắng (2A202602706) - Data Foundation & Observability  
3. Nguyễn Thị Vàng (2A202602897) - RAG, Vector Index & Benchmark  

> 💡 **File trình chiếu tương tác:** Nhóm có thể mở trực tiếp file [`docs/slides.html`](./slides.html) bằng bất kỳ trình duyệt nào (Chrome, Edge) để trình chiếu Fullscreen và xem gợi ý thuyết trình (Speaker Notes).

---

## Slide 1: Giới Thiệu & Mục Tiêu Đề Tài
- **Đề tài:** Data Pipeline & Data Observability cho Hệ Thống RAG Agent
- **Vấn đề thực chiến:**
  - Xây dựng Data Pipeline hoàn chỉnh, tự động hóa từ Raw Ingestion đến RAG Retrieval.
  - Tích hợp chốt kiểm dịch chất lượng tự động **Great Expectations 1.x (Fluent API)** & **Freshness SLA**.
  - Mô phỏng sự cố dữ liệu bẩn (**Synthetic Data Corruption**) và chứng minh năng lực **Tự phục hồi bất biến (Idempotent Self-Healing)**.

---

## Slide 2: Vấn Đề Cốt Lõi - Hiểm Họa "Silent Failure" trong RAG
- **Thực trạng đau đớn:** Khi dữ liệu bị lỗi (rác chuỗi, null, cắt cụt), hệ thống RAG **KHÔNG HỀ CRASH**:
  - Vector DB vẫn tính khoảng cách cosine và trả về top-k hàng xóm (dù là vector rác).
  - LLM vẫn mượt mà sinh ra câu trả lời dựa trên context nhiễu (Ảo giác tự tin - Confident Hallucination).
- **Hậu quả:** Lỗi diễn ra âm thầm, không phát sinh Exception trong log, chỉ phát hiện khi người dùng cuối phàn nàn.
- **Giải pháp:** Chốt chặn **Data Quality Gate** bắt buộc phải nằm ngay sau tầng Ingestion & Cleaning, trước khi nạp vào Vector Database.

---

## Slide 3: Kiến Trúc Tổng Thể & Luồng Dữ Liệu
1. **Raw Preservation (CP0):**
   - Tải 24 bài báo metadata từ Crossref REST API.
   - Luôn duy trì snapshot gốc tại `data/raw/crossref_records.json` có cơ chế Offline Fallback.
2. **Data Cleaning & Enrichment (CP1):**
   - Khử trùng lặp theo `paper_id`.
   - Tính toán trường thời gian thực `age_days` và ghép nối chuẩn `text_for_embedding`.
3. **Data Observability Gate (CP1):**
   - Great Expectations 1.x ephemeral suite thẩm định 4 kỳ vọng.
   - Freshness SLA giám sát tỷ lệ bài cũ quá 180 ngày.
4. **Vector Store & Evaluation (CP2 & CP3):**
   - ChromaDB nạp vector embedding từ `all-MiniLM-L6-v2` / Gemini.
   - Benchmark bộ test chuẩn gồm 10 câu hỏi chia 4 nhóm nghiệp vụ: *Summary, Author, Date, Category*.

---

## Slide 4: Data Observability với Great Expectations 1.x & Freshness SLA
- **Chuẩn GX 1.x Fluent API hiện đại:**
  - Khởi tạo Ephemeral Context (`mode="ephemeral"`).
  - Kết nối Pandas Data Source, Data Asset và Batch Definition.
- **4 Chốt kiểm dịch thiết yếu:**
  1. `ExpectTableRowCountToBeBetween`: Số dòng thuộc `[10, 50]`.
  2. `ExpectColumnValuesToNotBeNull`: `paper_id`, `title` không được rỗng.
  3. `ExpectColumnValuesToBeUnique`: Khóa chính `paper_id` duy nhất 100%.
  4. `ExpectColumnValueLengthsToBeBetween`: Tiêu đề tối thiểu &ge; 8 ký tự.
- **Freshness SLA:**
  - `age_days = (run_date - published).days`.
  - Cảnh báo vi phạm nếu tỷ lệ bài cũ > 180 ngày vượt quá 25%.
  - Kết quả Baseline: **`FRESH`** (Chỉ 1/24 bài cũ quá hạn).

---

## Slide 5: Kịch Bản Thử Nghiệm - Synthetic Data Corruption Suite
Chủ động tiêm 6 kịch bản lỗi thực tế mô phỏng sự cố môi trường Production:
1. **Drop latest records:** Mất 20% bản ghi mới do lỗi phân trang/timeout.
2. **Blank summary:** Xóa rỗng trường tóm tắt làm mất ngữ nghĩa cốt lõi.
3. **Inject noise:** Chèn chuỗi ký tự rác ngẫu nhiên làm méo không gian vector.
4. **Truncate title:** Cắt ngắn tiêu đề < 8 ký tự để kích hoạt cảnh báo GX.
5. **Stale date:** Lùi ngày xuất bản về quá khứ sâu để kiểm thử Freshness SLA.
6. **Duplicate rows:** Nhân bản dữ liệu làm biến dạng phân phối tìm kiếm.

---

## Slide 6: Bảng Đối Chiếu Định Lượng 3 Trạng Thái
*(Trích xuất trực tiếp từ `data/reports/corruption_report.md`)*

| Chỉ số quan sát | Baseline (Chuẩn) | Corrupted (Bị lỗi) | Repaired (Phục hồi) | Nhận xét thực nghiệm |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **1.0000 (100%)** | **0.6000 (60.0%)** | **1.0000 (100%)** | 📉 Tụt 40% khi tiêm lỗi &rarr; ✅ Khôi phục nguyên vẹn 100% |
| **Mean Token F1** | **0.8965 (89.7%)** | **0.6159 (61.6%)** | **0.8965 (89.7%)** | Độ chính xác câu trả lời trở lại mức nền xuất sắc |
| **Judge Accuracy** | **1.0000 (100%)** | **0.7000 (70.0%)** | **1.0000 (100%)** | LLM-as-a-judge đánh giá câu trả lời đạt điểm tối đa |
| **GX Quality Gate** | **PASS** | ❌ **FAIL** | ✅ **PASS** | Great Expectations 1.x phát hiện chính xác vi phạm |
| **Số lượng bản ghi** | 24 | 23 | 24 | Khôi phục nguyên vẹn cấu trúc dữ liệu |

---

## Slide 7: Cơ Chế Tự Phục Hồi Bất Biến (Idempotent Self-Repair)
- **Nguyên lý kiến trúc:** *Không bao giờ sửa lỗi trực tiếp trên dữ liệu bẩn (In-place patching).*
- **3 Cột trụ Idempotent:**
  1. **Nguồn thô bất biến (Raw Immutability):** `data/raw/crossref_records.json` luôn được giữ nguyên như một Snapshot tin cậy (Source of Truth).
  2. **Quy trình làm sạch xác định (Deterministic Cleaning):** Cùng đầu vào raw snapshot luôn sinh ra đúng 24 dòng sạch với cùng một phân phối dữ liệu.
  3. **Tái tạo chỉ mục an toàn (Clean Re-indexing):** Xóa bỏ hoàn toàn vector cũ và nạp lại từ đầu. Chạy 1 lần hay 100 lần thì kết quả cuối cùng vẫn hoàn toàn đồng nhất (Idempotent).

---

## Slide 8: Kịch Bản Live Demo & Sẵn Sàng Q&A
- **2 Lệnh Terminal thực chiến trên bảng:**
  ```bash
  # 1. Chạy Pha Chuẩn (Exit code 0, Hit Rate 100%)
  python script/run_phase1.py

  # 2. Tiêm Lỗi, Quan Sát Suy Thoái & Tự Phục Hồi (In bảng 3 trạng thái)
  python script/run_corruption_flow.py
  ```
- **Chuẩn bị trả lời câu hỏi chất vấn (Q&A Ready):**
  - *Câu hỏi:* Tại sao chọn Great Expectations 1.x ephemeral mode?
    - *Trả lời:* Ephemeral context chạy trực tiếp trong bộ nhớ (in-memory), không cần tạo thư mục `great_expectations/` nặng nề, hoàn hảo cho pipeline CI/CD và RAG agent.
  - *Câu hỏi:* Tại sao Hit Rate giảm từ 100% xuống 60% khi dữ liệu bị lỗi?
    - *Trả lời:* Lỗi xóa tóm tắt và chèn ký tự rác làm sai lệch embedding vector, khiến mô hình retrieval tìm nhầm tài liệu không chứa câu trả lời.
  - *Câu hỏi:* Tính Idempotent thể hiện ở đâu trong mã nguồn?
    - *Trả lời:* Thể hiện ở hàm `build_clean_dataframe()` và `rebuild index` nhận đầu vào từ file raw snapshot bất biến, cho đầu ra nhất quán mọi lần chạy.
