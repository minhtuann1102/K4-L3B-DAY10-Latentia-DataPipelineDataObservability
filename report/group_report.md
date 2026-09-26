# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo tổng kết chính thức của nhóm Latentia cho bài thực chiến Day 10: Data Pipeline, Data Observability và RAG Evaluation.

---

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3B                     |
| Tên nhóm         | Latentia                   |
| Repository         | https://github.com/minhtuann1102/K4-L3B-DAY10-Latentia-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Minh Tuấn | 2A202602420 | Techlead & Pipeline Integrator | `src/core/`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/` |
| 2 | Nguyễn Minh Thắng | 2A202602706 | Data Foundation & Observability | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/observability/quality.py` |
| 3 | Nguyễn Thị Vàng | 2A202602897 | RAG, Vector Index & Benchmark | `src/retrieval/embeddings.py`, `src/retrieval/index.py`, `src/evaluation/testset.py`, `src/ingestion/corruption.py` |

---

## 2. Tóm tắt kết quả

Nhóm Latentia đã hoàn thành toàn diện 100% các yêu cầu từ Checkpoint 0 đến Checkpoint 6 của bài Lab Day 10. Hệ thống đã xây dựng thành công Data Pipeline tự động hóa từ tầng Ingestion dữ liệu học thuật từ Crossref REST API (có cơ chế Offline Fallback bảo toàn 24 bản ghi gốc), chuẩn hóa schema, tính toán trường `text_for_embedding` và giám sát độ tươi `age_days`. Nhóm đã tích hợp chốt kiểm dịch chất lượng dữ liệu tự động sử dụng **Great Expectations 1.x (Fluent API & Ephemeral Context)** cùng hệ thống kiểm soát Freshness SLA (ngưỡng 180 ngày).

Để chứng minh hiểm họa **Silent Failure** trong các hệ thống RAG thực tế, nhóm đã tiêm 6 kịch bản Synthetic Data Corruption (mất bản ghi mới, rỗng tóm tắt, chèn chuỗi nhiễu, cắt ngắn tiêu đề, lùi ngày xuất bản và nhân bản dữ liệu). Kết quả thực nghiệm cho thấy hệ thống RAG không hề bị crash nhưng chất lượng trả lời sụt giảm nghiêm trọng: `retrieval_hit_rate` tụt từ **100% xuống 60%** (-40%) và `mean_token_f1` giảm từ **0.8965 xuống 0.6159**, trong khi chốt kiểm dịch Great Expectations lập tức bật cờ cảnh báo **`FAIL`**. Cơ chế **Idempotent Self-Repair** của nhóm kích hoạt khôi phục tự động từ Snapshot gốc bất biến (`crossref_records.json`), tái thực thi pipeline và tái lập chỉ mục ChromaDB, đưa toàn bộ chỉ số Retrieval Hit Rate, Token F1 và Quality Gate trở về trạng thái nền hoàn hảo (**100%**, `PASS`).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
[Crossref REST API] / [Local Fallback: data/raw/crossref_response.json]
       │
       ▼ (parse & preserve raw)
[data/raw/crossref_records.json] (Raw Immutability - Source of Truth)
       │
       ▼ (dedup by paper_id, compute age_days, build text_for_embedding)
[data/clean/papers_clean.csv & .json] (Clean Dataset - 24 rows)
       │
       ├──────────────────────────────────────────┐
       ▼ (Data Quality Gate)                      ▼ (Embedding & Indexing)
[Great Expectations 1.x & Freshness SLA]    [ChromaDB: papers-baseline]
(4 Expectations: Count, Unique, Null, Len)  (Gemini / all-MiniLM-L6-v2)
       │                                          │
       ▼ (data/quality/*.json)                    ▼ (Benchmark Evaluation)
[Quality Gate Status: PASS/FAIL]            [data/eval/test_set.json (10 Qs)]
                                                  │
                                                  ▼
                                            [Evaluation Metrics]
                                            (Hit Rate, Token F1, Judge Acc)
                                                  │
       ┌──────────────────────────────────────────┘
       ▼ (Experiment Flow)
[Synthetic Corruption: 6 Scenarios] ──► [Quality Gate: FAIL & Hit Rate: 60%]
       │
       ▼ (Trigger Idempotent Self-Repair from raw records)
[Repaired Clean & ChromaDB: papers-repaired] ──► [Quality Gate: PASS & Hit Rate: 100%]
       │
       ▼
[data/reports/corruption_report.md] (Báo cáo đối chiếu 3 trạng thái tự động)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | Crossref REST API / Snapshot local | Tải dữ liệu, fallback offline, parse metadata bảo toàn trường raw | `data/raw/crossref_records.json` | Nguyễn Minh Thắng |
| **Cleaning** | `List[PaperRecord]` | Khử trùng lặp `paper_id`, tính `age_days`, sinh `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Nguyễn Minh Thắng |
| **Observability** | Clean/Corrupted DataFrame | GX 1.x Ephemeral Suite (4 kỳ vọng), Freshness SLA (>180 ngày) | `data/quality/*_quality_report.json`, `freshness_report.json` | Nguyễn Minh Thắng |
| **Embedding/Index** | Clean/Corrupted/Repaired DataFrame | Đánh vector embeddings bằng Gemini/MiniLM, nạp ChromaDB collections | `data/embeddings/*.json`, `data/chroma/` | Nguyễn Thị Vàng |
| **Evaluation** | Clean DataFrame, Vector Index | Sinh bộ test set 10 câu hỏi (4 nhóm), đo Hit Rate & Token F1 | `data/eval/test_set.json`, `data/results/*_metrics.json` | Nguyễn Thị Vàng |
| **Corruption/Repair** | Clean DataFrame, Raw Snapshot | Tiêm 6 kịch bản lỗi, khôi phục idempotent từ snapshot gốc | `data/results/corruption_log.json`, `data/clean/*_repaired.*` | Nguyễn Thị Vàng |
| **Orchestration** | Cấu hình `Settings`, modules | Tích hợp luồng Phase 1, Corruption Flow, CLI & Web Hub | `script/run_phase1.py`, `script/run_corruption_flow.py`, `demo_hub.py` | Nguyễn Minh Tuấn |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `gemini` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `models/gemini-embedding-001` (hoặc `sentence-transformers/all-MiniLM-L6-v2`) |
| Số lượng Crossref records | `24` |
| Retrieval `top_k` | `4` |
| Freshness threshold | `180` ngày |
| Ephemeral GX Mode | `ephemeral` |

### Lệnh cài đặt môi trường

```bash
# Sử dụng virtual environment đã cấu hình
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### Lệnh chạy Pipeline

```bash
# 1. Chạy Baseline Pipeline (Pha chuẩn)
python script/run_phase1.py

# 2. Chạy Luồng Tiêm Lỗi & Tự Phục Hồi (Corruption & Repair Flow)
python script/run_corruption_flow.py

# 3. Khởi động Web Demo & Presentation Hub (Giao diện Live Demo)
python script/demo_hub.py
```

### Kết quả tái hiện thực tế

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| :--- | :---: | :---: | :--- |
| **Baseline pipeline** (`run_phase1.py`) | Thành công (Exit 0) | 2026-09-26 11:37:10 UTC+7 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| **Corruption flow** (`run_corruption_flow.py`) | Thành công (Exit 0) | 2026-09-26 11:40:22 UTC+7 | `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, Cleaning và Data Contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| :--- | :--- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query=agentic+retrieval+augmented+generation+large+language+model`, `filter=has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-26T10:04:40+07:00 |
| Số record nhận được | 24 bản ghi học thuật hợp lệ |
| Cơ chế retry/backoff | Timeout 15s; khi gặp lỗi kết nối hoặc HTTP 429 lập tức tự động fallback sang `data/raw/crossref_response.json` |

### Raw và Clean Schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| :--- | :--- | :---: | :--- | :--- |
| `paper_id` | `str` (DOI) | Có | Định danh duy nhất toàn cầu của bài báo | Loại bỏ bản ghi nếu rỗng |
| `title` | `str` | Có | Tiêu đề chính của ấn phẩm | Strip khoảng trắng; GX chặn nếu length < 8 |
| `published` | `datetime / str` | Có | Ngày xuất bản theo định dạng ISO | Chuẩn hóa UTC, parse về datetime để tính age |
| `authors` | `list[str]` | Không | Danh sách tác giả nghiên cứu | Chuẩn hóa `unknown`, ghép nối `authors_joined` |
| `categories` | `list[str]` | Không | Chủ đề/lĩnh vực nghiên cứu | Điền `General Computer Science` nếu thiếu |
| `summary` | `str` | Có | Tóm tắt (Abstract) bài báo | Bóc tách HTML tags, fallback về title nếu thiếu |
| `text_for_embedding` | `str` | Có | Đoạn văn bản hoàn chỉnh phục vụ vector hóa | Ghép `Title: ... \nAuthors: ... \nSummary: ...` |
| `age_days` | `int` | Có | Số ngày tuổi từ ngày xuất bản đến hiện tại | `(run_date - published).days`, tối thiểu 0 |

### Quy tắc cleaning

1. **Khử trùng lặp (Deduplication):** Loại bỏ triệt để các bài trùng `paper_id`, chỉ giữ lại bản ghi xuất hiện đầu tiên.
2. **Làm sạch văn bản (Sanitization):** Loại bỏ các thẻ định dạng XML/HTML `<jats:p>`, `<jats:title>` phát sinh từ API Crossref.
3. **Tạo trường embedding (`text_for_embedding`):**
   ```python
   text_for_embedding = f"Title: {title}\nAuthors: {authors_joined}\nPublished: {published}\nCategories: {categories_joined}\nSummary: {summary}"
   ```
4. **Tính tuổi dữ liệu (`age_days`):** Lấy hiệu số ngày giữa `run_date` (UTC) và `published`.

---

## 6. Evaluation Setup

| Thành phần | Cấu hình thực tế |
| :--- | :--- |
| Số câu hỏi benchmark | 10 câu hỏi chuẩn hóa |
| Các `question_type` | 4 nhóm nghiệp vụ: `summary` (4 câu), `authors` (2 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID | Trích xuất trực tiếp từ `paper_id` của tài liệu sinh ra câu hỏi trong `data/eval/test_set.json` |
| Embedding model | `models/gemini-embedding-001` (với cơ chế Retry Exponential Backoff 5 lần) |
| Vector store / Collection | ChromaDB (Cosine distance): `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | `4` |
| Test set dùng chung | Cùng 1 file [data/eval/test_set.json](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/data/eval/test_set.json) cho cả 3 trạng thái |

> **Tại sao test set phải được giữ nguyên qua 3 trạng thái?**  
> Việc giữ nguyên tập 10 câu hỏi test benchmark là nguyên tắc then chốt của khoa học thực nghiệm (Controlled Experiment). Khi bộ câu hỏi và ground-truth được cố định, mọi biến thiên trong chỉ số Hit Rate và Token F1 chỉ phản ánh chính xác một biến số duy nhất: **chất lượng của kho dữ liệu (Data Quality)** tại trạng thái đó, loại bỏ hoàn toàn nhiễu do câu hỏi thay đổi.

---

## 7. Kết quả Baseline (Pha 1)

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| :--- | :--- | :---: | :--- |
| Raw records snapshot | `data/raw/crossref_records.json` | Có | 24 bản ghi gốc |
| Cleaned dataset | `data/clean/papers_clean.csv` & `.json` | Có | 24 dòng sạch đầy đủ trường |
| Embedding manifest | `data/embeddings/papers_embeddings.json` | Có | Backend ChromaDB, 24 vectors |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu hỏi qua 4 nhóm nghiệp vụ |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit rate = 1.0, Token F1 = 0.8965 |
| Quality & Freshness report | `data/quality/baseline_quality_report.json` | Có | GX Success = True, Fresh = True |
| Phase 1 report | `data/reports/phase1_report.md` | Có | Báo cáo Markdown tự động |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| :--- | :---: | :--- |
| `retrieval_hit_rate` | **1.0000 (100%)** | 10/10 câu hỏi tìm thấy đúng tài liệu ground-truth trong top 4 kết quả |
| `mean_token_f1` | **0.8965 (89.7%)** | Độ trùng khớp token giữa câu trả lời sinh ra và ground truth đạt mức xuất sắc |
| `judge_accuracy` | **1.0000 (100%)** | Toàn bộ 10 câu trả lời được LLM-as-a-judge đánh giá chính xác và đầy đủ |
| `mean_judge_score` | **1.0000 (1.0/1.0)** | Điểm số đánh giá định tính tuyệt đối |

---

## 8. Data Quality & Freshness Observability

### Quality Checks (Great Expectations 1.x)

| Check (Expectation) | Quality Dimension | Ngưỡng / Kỳ vọng | Kết quả Baseline | Bằng chứng |
| :--- | :--- | :--- | :---: | :--- |
| `ExpectTableRowCountToBeBetween` | Completeness | Min: 10, Max: 50 | **PASS** (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` | Validity | `paper_id` & `title` không rỗng | **PASS** (0 nulls) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` | Uniqueness | `paper_id` duy nhất 100% | **PASS** (0 duplicates) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` | Integrity | `title` độ dài [8, 500] ký tự | **PASS** (min: 24 ký tự) | `baseline_quality_report.json` |

### Freshness SLA Monitoring

| Thuộc tính | Giá trị thực tế |
| :--- | :--- |
| Vị trí đo lường | `data/clean/papers_clean.csv` |
| Công thức tính | `age_days = (run_date - published).days` |
| Ngưỡng Freshness SLA | Tỷ lệ bài có `age_days > 180` không được vượt quá `25%` |
| Số bài cũ quá hạn | 1 / 24 bài (4.17%) |
| Trạng thái Baseline | **`FRESH`** (`is_fresh: true`) |

---

## 9. Kịch bản Corruption & Cơ chế Repair

| Kịch bản Corruption | Cách tạo lỗi thực tế | Record bị tác động | Quality signal phát hiện | Tác động thực tế lên RAG | Cách Repair |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **1. Drop Latest** | Xóa 20% bản ghi mới nhất | 4 bài báo | Row count giảm xuống 20 | Mất tài liệu ground-truth mới | Nạp lại đầy đủ từ snapshot gốc |
| **2. Blank Summary** | Gán `summary = ""` | 3 bài báo | `text_for_embedding` rỗng nội dung | Vector embedding mất ngữ nghĩa | Khôi phục abstract từ raw record |
| **3. Inject Noise** | Chèn chuỗi ký tự rác ngẫu nhiên | 3 bài báo | Embedding vector bị lệch tâm | Sai lệch similarity score | Loại bỏ nhiễu, tái tạo text sạch |
| **4. Truncate Title** | Cắt ngắn title còn `< 8` ký tự | 2 bài báo | **GX Length Expectation FAIL** | Exact title match thất bại | Phục hồi title nguyên bản |
| **5. Stale Date** | Lùi ngày xuất bản về quá khứ sâu | 3 bài báo | Freshness stale count tăng | Vi phạm Freshness SLA nếu quá 25% | Khôi phục date chuẩn từ API |
| **6. Duplicate Rows** | Nhân bản dòng ngẫu nhiên | 2 bài báo | **GX Unique Expectation FAIL** | Biến dạng phân phối top-k | Dedup bằng `drop_duplicates("paper_id")` |

Log chi tiết quá trình tiêm lỗi được lưu trữ minh bạch tại [data/results/corruption_log.json](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/data/results/corruption_log.json).

---

## 10. Bảng Đối Chiếu 3 Trạng Thái (Baseline vs Corrupted vs Repaired)

*(Trích xuất trực tiếp từ kết quả chạy thực nghiệm tại `data/reports/corruption_report.md`)*

| Metric / Signal | 1. Baseline | 2. Corrupted | 3. Repaired | Delta do Corruption | Mức phục hồi sau Repair | Đánh giá quan sát |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **1.0000 (100%)** | **0.6000 (60.0%)** | **1.0000 (100%)** | **-40.0%** | **+40.0% (100% recovery)** | 📉 Suy thoái ngầm (Silent Failure) &rarr; ✅ Phục hồi hoàn hảo |
| **`mean_token_f1`** | **0.8965 (89.7%)** | **0.6159 (61.6%)** | **0.8965 (89.7%)** | **-28.06%** | **+28.06%** | Câu trả lời bị sai lệch nội dung khi dính lỗi tóm tắt và rác |
| **`judge_accuracy`** | **1.0000 (100%)** | **0.7000 (70.0%)** | **1.0000 (100%)** | **-30.0%** | **+30.0%** | Độ chính xác LLM-as-a-judge khôi phục tuyệt đối |
| **`GX Quality Gate`** | **PASS** | ❌ **FAIL** | ✅ **PASS** | `True` &rarr; `False` | `False` &rarr; `True` | Chốt kiểm dịch Great Expectations phát hiện chuẩn xác |
| **`Freshness Status`** | **FRESH** | **FRESH (4 stale)** | **FRESH (1 stale)** | Tăng bài cũ | Trở về ngưỡng chuẩn | SLA duy trì trong giới hạn kiểm soát |
| **Số lượng bản ghi** | 24 | 23 | 24 | -1 dòng | Đủ 24 dòng | Cấu trúc dữ liệu khôi phục nguyên vẹn |

### Hai chuỗi quan hệ Nhân Quả then chốt:

1. **Chuỗi Sự Cố (Data Corruption &rarr; Silent Failure):**
   Tiêm lỗi xóa tóm tắt và chèn ký tự rác &rarr; Great Expectations phát hiện vi phạm độ dài và tính duy nhất (`Quality Gate: FAIL`) &rarr; Vector representation bị biến dạng, kéo theo `retrieval_hit_rate` tụt dốc từ 100% xuống 60% (-40%). Mặc dù ứng dụng không hề crash, người dùng nhận được câu trả lời thiếu thông tin hoặc sai lệch.
2. **Chuỗi Tự Phục Hồi (Idempotent Repair &rarr; Quality Restoration):**
   Kích hoạt luồng phục hồi từ bản lưu trữ thô bất biến (`crossref_records.json`) &rarr; Quy trình Cleaning tái tạo tập 24 bản ghi chuẩn (`Quality Gate: PASS`) &rarr; ChromaDB được tái tạo sạch (`papers-repaired`), đưa `retrieval_hit_rate` và `mean_token_f1` trở lại đúng mức Baseline ban đầu (100% và 89.65%).

---

## 11. Vấn đề tích hợp kỹ thuật quan trọng đã giải quyết

### Sự cố 1: Lỗi DNS / Network Jitter khi gọi API Embedding
- **Triệu chứng:** Khi chạy luồng đánh giá với Gemini Embeddings trên mạng Wi-Fi giảng đường, xuất hiện lỗi `httpcore.ConnectError: [Errno 11001] getaddrinfo failed`.
- **Nguyên nhân:** Cuộc gọi mạng đến endpoint Google GenAI bị ngắt quãng chập chờn hoặc timeout DNS.
- **Cách xử lý:** Bổ sung cơ chế **Retry với Exponential Backoff (5 lần thử, độ trễ `1.5 * (attempt + 1)` giây)** tại [src/retrieval/embeddings.py](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/src/retrieval/embeddings.py).
- **Kết quả:** Pipeline chạy trơn tru 100%, tự động vượt qua các đợt rớt mạng tạm thời mà không bị ngắt quãng giữa chừng.

### Sự cố 2: Nâng cấp cú pháp Great Expectations 1.x Fluent API
- **Triệu chứng:** Great Expectations phiên bản 1.16+ báo lỗi khi sử dụng cú pháp `DataContext` và `ExpectationSuite` cũ dạng file cấu hình tĩnh.
- **Nguyên nhân:** GX 1.x chuyển dịch hoàn toàn sang kiến trúc Fluent API với Ephemeral Data Sources.
- **Cách xử lý:** Cấu hình chuẩn `gx.get_context(mode="ephemeral")`, định nghĩa `add_pandas()`, `add_dataframe_asset()`, và `add_batch_definition_whole_dataframe()` tại [src/observability/quality.py](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/src/observability/quality.py).
- **Kết quả:** Code chạy sạch sẽ, không phụ thuộc thư mục rác trên đĩa, thời gian kiểm dịch chỉ mất dưới 0.15 giây.

---

## 12. Giới hạn hiện tại và hướng phát triển

| Giới hạn hiện tại | Mức độ ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| :--- | :--- | :--- |
| **Quy mô dữ liệu còn nhỏ** (24 bài báo) | Phù hợp cho bài lab thực chiến 4 giờ nhưng chưa thử thách được độ trễ khi quy mô lên tới hàng triệu vector | Tích hợp Batch Ingestion đa luồng (`concurrent.futures`) và phân mảnh collection theo thời gian |
| **Độ đa dạng của câu hỏi test** (10 câu) | Đủ đại diện cho 4 nhóm nghiệp vụ nhưng chưa bao quát hết các câu hỏi suy luận phức hợp đa chặng (Multi-hop Reasoning) | Mở rộng lên 50 câu hỏi tự động sinh qua kỹ thuật Testset Synthesis của Ragas |
| **Cơ chế Repair phụ thuộc Snapshot Local** | Nếu file raw snapshot bị hỏng vật lý trên đĩa thì cần gọi lại API | Thiết lập cơ chế Cloud Object Storage Backup (S3 / GCS bucket có versioning) cho tầng Raw Data |

---

## 13. Checklist nghiệm thu bài nộp

- [x] Thông tin nhóm và đường dẫn GitHub repository chính xác 100%.
- [x] Phân công vai trò khớp với commit Git và mã nguồn thực tế.
- [x] Lệnh chạy `script/run_phase1.py` và `script/run_corruption_flow.py` đều kết thúc với Exit Code 0.
- [x] Cả 3 trạng thái đều sử dụng cùng 1 bộ test benchmark `data/eval/test_set.json`.
- [x] Bảng số liệu đối chiếu 3 trạng thái khớp 100% với các file JSON trong `data/results/`.
- [x] Đã hoàn thành bộ Slide thuyết trình tương tác tại `docs/slides.html` và Web Hub tại `docs/demo_hub.html`.
- [x] Từng thành viên đã hoàn thiện báo cáo vai trò cá nhân riêng biệt trong thư mục `report/`.
- [x] Tuyệt đối không commit file `.env`, khóa API, token bí mật hay thư mục tạm `chroma/`, `.venv/` lên Git.
