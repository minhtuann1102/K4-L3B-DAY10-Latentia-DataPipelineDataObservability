# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo vai trò cá nhân: Nguyễn Thị Vàng (RAG, Vector Index & Benchmark Evaluation).

---

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Nguyễn Thị Vàng            |
| MSSV               | 2A202602897                |
| Khóa/Lớp           | K4-L3B                     |
| Tên nhóm           | Latentia                   |
| Vai trò chính      | RAG, Vector Index & Benchmark (`embeddings.py`, `index.py`, `testset.py`, `corruption.py`) |
| Repository         | https://github.com/minhtuann1102/K4-L3B-DAY10-Latentia-DataPipelineDataObservability |
| Ngày hoàn thành    | 2026-09-26                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| **Benchmark Testset Generation** | `src/evaluation/testset.py` | Cleaned DataFrame | `data/eval/test_set.json` (10 câu hỏi qua 4 nhóm nghiệp vụ) | Hoàn thành |
| **Vector Indexing & ChromaDB** | `src/retrieval/embeddings.py`, `src/retrieval/index.py` | Clean DataFrame, Embedding model | ChromaDB collections (`papers-baseline`, `papers-corrupted`, `papers-repaired`) | Hoàn thành |
| **Synthetic Data Corruption Suite** | `src/ingestion/corruption.py` | Clean DataFrame | Corrupted DataFrame (6 loại lỗi) & `data/results/corruption_log.json` | Hoàn thành |
| **RAG Retrieval & Evaluation Engine** | `src/evaluation/metrics.py`, `src/retrieval/qa.py` | Test set, Vector index, LLM | `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| --------- | ----------------------------- | --------------------- |
| Phối hợp chốt kiểm dịch chất lượng | Nguyễn Minh Thắng (`quality.py`) | Đảm bảo các kịch bản tiêm lỗi (như cắt ngắn title) kích hoạt chính xác các Expectation tương ứng |
| Hỗ trợ xây dựng giao diện Live Demo | Nguyễn Minh Tuấn (`demo_hub.html`) | Cung cấp danh sách các câu hỏi test mẫu cho khung RAG Query Sandbox trên Web Hub |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết kế bộ câu hỏi Benchmark đa dạng | `src/evaluation/testset.py` | 10 câu hỏi chuẩn hóa thuộc 4 nhóm nghiệp vụ: `summary`, `authors`, `date`, `categories` | File [data/eval/test_set.json](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/data/eval/test_set.json) |
| Xây dựng và quản lý Vector Index | `src/retrieval/index.py` | Đánh chỉ mục 24 documents với không gian khoảng cách Cosine trên ChromaDB | File `data/embeddings/papers_embeddings.json` |
| Tiêm 6 kịch bản Synthetic Corruption | `src/ingestion/corruption.py` | Gây ra sự cố dữ liệu bẩn có chủ đích để mô phỏng Silent Failure | File `data/results/corruption_log.json` |
| Đo lường hiệu năng 3 trạng thái | `src/evaluation/metrics.py` | Tính toán chính xác Hit Rate (1.0 &rarr; 0.6 &rarr; 1.0) và Token F1 (0.8965 &rarr; 0.6159 &rarr; 0.8965) | `data/results/*_metrics.json` |

Output cụ thể: File [data/eval/test_set.json](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/data/eval/test_set.json) gồm 10 câu hỏi có cấu trúc chặt chẽ kèm theo `ground_truth_doc_ids` chuẩn xác.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Đánh giá hệ thống RAG không thể chỉ dựa vào cảm quan mà cần một bộ test set chuẩn hóa đại diện cho nhiều góc độ nghiệp vụ truy vấn.
2. Cần mô phỏng được tác động tiêu cực của dữ liệu lỗi lên vector space (sự xáo trộn khoảng cách ngữ nghĩa giữa query và documents).
3. Đo lường chính xác mức độ suy thoái ngầm (Silent Failure) bằng các chỉ số định lượng: Retrieval Hit Rate (tỷ lệ tìm trúng tài liệu) và Token F1 (độ trùng khớp ngữ nghĩa của câu trả lời).

### Cách triển khai
1. **Thiết kế Benchmark Test Set:** Trong `src/evaluation/testset.py`, viết logic sinh 10 câu hỏi bao quát 4 nhóm:
   - Nhóm `summary`: Câu hỏi yêu cầu tóm tắt nội dung chính của bài báo.
   - Nhóm `authors`: Câu hỏi kiểm tra tác giả nghiên cứu (`Who authored...`).
   - Nhóm `date`: Câu hỏi kiểm tra thời gian xuất bản (`When was... published?`).
   - Nhóm `categories`: Câu hỏi kiểm tra lĩnh vực nghiên cứu (`What categories...`).
2. **Synthetic Data Corruption:** Trong `src/ingestion/corruption.py`, triển khai 6 hàm biến đổi:
   - `_drop_latest_records`: Cắt bỏ 20% bản ghi mới nhất.
   - `_blank_summary`: Xóa rỗng trường tóm tắt.
   - `_inject_noise`: Chèn chuỗi ký tự ngẫu nhiên vào tóm tắt.
   - `_truncate_title`: Cắt tiêu đề ngắn hơn 8 ký tự.
   - `_stale_date`: Lùi ngày xuất bản về quá khứ xa.
   - `_duplicate_rows`: Sao chép nhân bản các dòng ngẫu nhiên.
3. **Đo lường Metrics:**
   - `Hit Rate@K`: 1.0 nếu có ít nhất 1 `ground_truth_doc_id` nằm trong danh sách `top_k` retrieved documents, ngược lại 0.0.
   - `Token F1`: Tính độ giao hòa giữa tập tokens của ground truth và tokens của câu trả lời sinh ra.

### Input, Output và Contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | `papers_clean.csv`, `papers_clean.json` |
| Output | `data/eval/test_set.json`, `corruption_log.json`, `*_metrics.json` |
| Module phụ thuộc | `chromadb`, `sentence-transformers` / `google-genai` |
| Module sử dụng output | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| Xử lý lỗi | Kiểm tra tồn tại collection trong ChromaDB trước khi delete/rebuild; bọc embedding API với cơ chế retry |

### Cách xác minh thực tế

```bash
# Kiểm tra bộ Test Set
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Sinh được {len(ts)} câu hỏi test')"

# Kiểm tra Index và Retrieval QA
python -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; from retrieval.qa import answer_question; s=load_settings(); idx=LocalEmbeddingIndex(settings=s); res=answer_question(\"Who authored 'Mitigating Ghost Vectors in Dense Retrieval via Idempotent Indexing'?\", settings=s, index=idx); print('Answer:', res.answer)"
```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn chiến lược đánh giá câu trả lời của RAG: Sử dụng LLM-as-a-judge hay Token-level F1 metric?
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (Chỉ dùng LLM-as-a-judge):* Đưa câu trả lời và ground truth cho mô hình LLM chấm điểm từ 1 đến 5 hoặc True/False.
  - *Phương án 2 (Kết hợp cả Token F1 và Retrieval Hit Rate cùng LLM Judge):* Sử dụng Retrieval Hit Rate làm chỉ số cứng đo tầng retrieval, Token F1 đo độ chính xác trích xuất từ vựng, và LLM Judge đo tính mạch lạc ngữ nghĩa.
- **Phương án đã chọn:** Phương án 2 (Đa chỉ số kết hợp).
- **Lý do:** LLM-as-a-judge tốn chi phí API, có độ trễ và có thể gặp hiện tượng không nhất quán (non-deterministic). Việc kết hợp Retrieval Hit Rate (khách quan 100%) và Token F1 giúp nhóm có thước đo vừa nhanh, vừa hoàn toàn độc lập và kiểm chứng được bằng toán học.
- **Bằng chứng:** Bảng đối chiếu 3 trạng thái phản ánh rất rõ: Retrieval Hit Rate tụt chính xác 40%, Token F1 tụt 28.06% khi tiêm lỗi, và cả hai đều phục hồi 100% sau khi sửa dữ liệu.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi truy vấn trực tiếp câu hỏi trên khung Sandbox của Web Hub, hệ thống báo lỗi 500:
  `TypeError: LocalEmbeddingIndex.__init__() missing 2 required positional arguments: 'documents' and 'persist_path'`.
- **Nguyên nhân gốc:** Hàm khởi tạo `LocalEmbeddingIndex.__init__` bắt buộc phải truyền vào `documents` và `persist_path`, nhưng khi gọi từ API server độc lập, các tham số này không được cung cấp mặc định.
- **Cách xử lý:** Cập nhật `LocalEmbeddingIndex.__init__` tại `src/retrieval/index.py` để hỗ trợ giá trị mặc định: tự động tải `clean_json` nếu `documents` là `None`, và lấy `settings.paths.chroma_dir` nếu `persist_path` là `None`.
- **Cách xác minh sau khi sửa:** Chạy kiểm thử truy vấn câu hỏi *"Who authored 'Mitigating Ghost Vectors...'?"*, hệ thống trả về đúng tác giả `"Duc Vu, Thao Dang"` ngay lập tức.
- **Điều học được:** Khi thiết kế các lớp Core Engine (như Vector Index), cần thiết kế hàm khởi tạo linh hoạt với các giá trị mặc định hợp lý (Defensive Programming) để thuận tiện cho cả việc chạy theo kịch bản và chạy dưới dạng API phục vụ người dùng.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Ingestion API lấy metadata &rarr; lưu Snapshot `crossref_records.json` &rarr; làm sạch, khử trùng lặp và tính `text_for_embedding` &rarr; kiểm tra qua Great Expectations 1.x &rarr; Vector hóa bằng mô hình embedding &rarr; nạp vào collection ChromaDB.
2. **Evaluation set và ground-truth document IDs:** Bộ test set gồm 10 câu hỏi có kèm danh sách `ground_truth_doc_ids`. Khi RAG truy vấn, hệ thống kiểm tra xem ID của các tài liệu trích xuất được (Top-k) có chứa ground-truth ID hay không để tính Hit Rate, và tính Token F1 giữa câu trả lời sinh ra với câu trả lời chuẩn.
3. **Quality checks vs Freshness monitoring:** Quality checks (GX 1.x) kiểm tra tính đúng đắn cấu trúc dữ liệu (số dòng, not-null, unique, độ dài ký tự). Freshness monitoring kiểm tra tính hợp thời (SLA thời gian: tài liệu có bị quá cũ so với ngưỡng 180 ngày hay không).
4. **Vì sao dùng cùng test set cho 3 trạng thái:** Để đảm bảo tính chuẩn tắc của phương pháp thực nghiệm có đối chứng. Khi cố định câu hỏi và đáp án, mọi sự thay đổi điểm số hoàn toàn do chất lượng dữ liệu quyết định.
5. **Repair được xem là thành công khi:** Quality Gate chuyển từ `FAIL` về `PASS`, `retrieval_hit_rate` phục hồi từ 0.6000 về 1.0000, và báo cáo `corruption_report.md` xác nhận độ lệch delta = 0.0000 so với baseline.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.6000** | **1.0000** | Bị ảnh hưởng nặng nhất bởi kịch bản blank summary và drop latest |
| `mean_token_f1` | **0.8965** | **0.6159** | **0.8965** | Độ chính xác câu trả lời giảm sút nghiêm trọng khi dữ liệu bị tiêm nhiễu |
| `judge_accuracy` | **1.0000** | **0.7000** | **1.0000** | Phục hồi hoàn hảo sau quy trình tự sửa lỗi Idempotent |
| Quality checks | **PASS** | **FAIL** | **PASS** | Bắt lỗi chính xác |
| Freshness status | **FRESH** | **FRESH** | **FRESH** | Đảm bảo tính tươi mới dữ liệu qua các pha |

### Kết luận từ số liệu:
Kịch bản làm mất mát chất lượng RAG nghiêm trọng nhất là **Blank Summary** và **Drop Latest Records**: khi tài liệu bị mất tóm tắt hoặc bị xóa mất bản ghi mới, vector space bị thiếu hụt hoàn toàn thông tin ngữ nghĩa, dẫn đến việc mô hình retrieval không thể tìm thấy tài liệu gốc (Hit Rate rớt từ 100% xuống 60%).

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. Hiểu được cơ chế tác động trực tiếp của Data Corruption lên không gian vector: Dữ liệu bẩn làm méo mó vector embedding, gây ra hiện tượng ảo giác nghiêm trọng cho LLM.
2. Nắm vững phương pháp xây dựng Benchmark Test Set chuẩn hóa cho RAG với ground-truth mapping đa chiều.
3. Kỹ năng thiết kế các bài kiểm thử tự động (Unit Test / Metric Evaluation) cho các hệ thống AI phục vụ sản xuất.

### Nếu có thêm thời gian:
Tôi sẽ nghiên cứu và áp dụng thêm các kỹ thuật Re-ranking (Cross-Encoder) sau tầng Dense Retrieval để tăng cường độ chính xác tìm kiếm ngay cả khi dữ liệu có độ nhiễu nhẹ.
