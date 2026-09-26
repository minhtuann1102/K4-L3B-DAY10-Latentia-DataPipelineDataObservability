# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo vai trò cá nhân: Nguyễn Minh Thắng (Data Foundation & Observability).

---

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Nguyễn Minh Thắng          |
| MSSV               | 2A202602706                |
| Khóa/Lớp           | K4-L3B                     |
| Tên nhóm           | Latentia                   |
| Vai trò chính      | Data Foundation & Quality Gate (`crossref.py`, `cleaning.py`, `quality.py`) |
| Repository         | https://github.com/minhtuann1102/K4-L3B-DAY10-Latentia-DataPipelineDataObservability |
| Ngày hoàn thành    | 2026-09-26                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| **Ingestion & Offline Fallback** | `src/ingestion/crossref.py` | Crossref REST API / Snapshot local | `data/raw/crossref_records.json` (24 bản ghi gốc) | Hoàn thành |
| **Data Cleaning & Schema Enrichment** | `src/ingestion/cleaning.py` | `List[PaperRecord]` | `data/clean/papers_clean.csv`, `papers_clean.json` có `text_for_embedding` & `age_days` | Hoàn thành |
| **Data Observability (GX 1.x & Freshness)** | `src/observability/quality.py` | Cleaned / Corrupted DataFrame | Ephemeral Suite validation results, Freshness SLA report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| --------- | ----------------------------- | --------------------- |
| Hỗ trợ thiết kế kịch bản Corruption | Nguyễn Thị Vàng (`corruption.py`) | Định nghĩa các ngưỡng vi phạm cho 6 loại lỗi dữ liệu khớp với các check của GX |
| Kiểm thử tích hợp luồng Phase 1 | Nguyễn Minh Tuấn (`phase1.py`) | Đảm bảo dataframe đầu ra từ tầng cleaning tương thích hoàn hảo với ChromaDB vector index |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Xây dựng Ingestion Engine với Fallback | `src/ingestion/crossref.py` | Tải dữ liệu từ API Crossref, tự động fallback sang `crossref_response.json` khi có sự cố mạng | Console in: `Loaded 24 records` |
| Làm sạch và làm giàu trường dữ liệu | `src/ingestion/cleaning.py` | Khử trùng lặp theo `paper_id`, tính `age_days`, tạo trường chuẩn `text_for_embedding` | `data/clean/papers_clean.csv` (24 dòng) |
| Thiết lập chốt kiểm dịch Great Expectations 1.x | `src/observability/quality.py` | Triển khai Fluent API Ephemeral Context với 4 kỳ vọng then chốt | `data/quality/baseline_quality_report.json` (`success=True`) |
| Giám sát Freshness SLA | `src/observability/quality.py` | Đo lường tỷ lệ bài quá 180 ngày tuổi (&le; 25%) | `data/quality/freshness_report.json` (`is_fresh=True`) |

Output cụ thể: File [data/quality/baseline_quality_report.json](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/data/quality/baseline_quality_report.json) ghi nhận 4/4 expectations vượt qua với trạng thái `success: true`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. Dữ liệu từ API bên thứ ba (Crossref) có độ tin cậy không ổn định: dễ bị rate limit (HTTP 429), mất kết nối hoặc schema bị thiếu trường tóm tắt (abstract).
2. Dữ liệu thô chứa thẻ HTML/XML rác (`<jats:p>`), trùng lặp DOI, và không có cấu trúc thống nhất để làm đầu vào cho mô hình Vector Embedding.
3. Cần một chốt kiểm dịch chất lượng tự động (Data Quality Gate) hiện đại theo chuẩn Great Expectations 1.x để phát hiện ngay lập tức dữ liệu lỗi trước khi nạp vào Vector Database.

### Cách triển khai
1. **Fallback Snapshot:** Trong `fetch_source_records()`, nếu request tới API Crossref thất bại (timeout, 429, no internet), hàm lập tức chuyển sang đọc từ file snapshot lưu trữ sẵn tại `data/raw/crossref_response.json`.
2. **Data Cleaning & Enrichment:**
   - Sử dụng `df.drop_duplicates(subset=["paper_id"], keep="first")`.
   - Tính tuổi dữ liệu: `age_days = (run_date - published).dt.days`.
   - Chuẩn hóa văn bản embedding: ghép nối `Title`, `Authors`, `Published`, `Categories`, `Summary`.
3. **Great Expectations 1.x Fluent API:**
   Khởi tạo `context = gx.get_context(mode="ephemeral")`, thêm Pandas Data Source, Dataframe Asset và Batch Definition. Khởi tạo `suite = ExpectationSuite(name=...)` và thêm 4 kỳ vọng:
   - `gxe.ExpectTableRowCountToBeBetween(min_value=10, max_value=50)`
   - `gxe.ExpectColumnValuesToNotBeNull(column="paper_id")`
   - `gxe.ExpectColumnValuesToBeUnique(column="paper_id")`
   - `gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8)`

### Input, Output và Contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | Raw JSON payload từ Crossref hoặc snapshot |
| Output | `pd.DataFrame` 24 dòng sạch + Quality Validation JSON Report |
| Module phụ thuộc | `great_expectations 1.16+`, `pandas` |
| Module sử dụng output | `src/retrieval/index.py` (Vector Store) |
| Xử lý lỗi | Bóc tách an toàn các trường JSON lồng nhau (`author`, `abstract`, `created`) bằng hàm getter an toàn |

### Cách xác minh thực tế

```bash
# Kiểm tra Ingestion và Cleaning
python -c "from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; from datetime import datetime, timezone; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Clean thành công {len(df)} dòng')"

# Kiểm tra Great Expectations 1.x
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Quality status: {res[\"success\"]}')"
```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức triển khai Great Expectations giữa file-based context truyền thống (`great_expectations.yml`) và Ephemeral In-Memory Context mới trong GX 1.x.
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (File-based Context):* Khởi tạo thư mục `great_expectations/` với các file YAML cấu hình data source và checkpoints.
  - *Phương án 2 (Ephemeral Context):* Khởi tạo ngữ cảnh in-memory thông qua `gx.get_context(mode="ephemeral")` sử dụng Fluent API của GX 1.x.
- **Phương án đã chọn:** Phương án 2 (Ephemeral Context).
- **Lý do:** Ephemeral Context chạy hoàn toàn trong RAM, không sinh rác file hệ thống, không yêu cầu phân quyền ghi thư mục phức tạp, cực kỳ nhẹ và phù hợp hoàn hảo với kiến trúc pipeline CI/CD hiện đại.
- **Bằng chứng:** Thời gian thực thi toàn bộ 4 checks trên 24 bản ghi chỉ mất chưa đầy 0.15 giây, tích hợp mượt mà vào cả `run_phase1.py` và `run_corruption_flow.py`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi chạy `run_data_quality_checks()`, console cảnh báo:
  `UserWarning: Please initialize your DataContext using Great Expectations 1.0 conventions.` hoặc crash khi gọi `context.sources.add_pandas()`.
- **Nguyên nhân gốc:** Great Expectations từ phiên bản 1.0 trở đi đã thay đổi cú pháp: `context.sources` đổi thành `context.data_sources`, và việc tạo batch phải thông qua `add_batch_definition_whole_dataframe()`.
- **Cách xử lý:** Tái cấu trúc hoàn toàn hàm theo chuẩn GX 1.x Fluent API:
  ```python
  context = gx.get_context(mode="ephemeral")
  data_source = context.data_sources.add_pandas(name="papers_source")
  data_asset = data_source.add_dataframe_asset(name="papers_asset")
  batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
  batch = batch_def.get_batch(batch_parameters={"dataframe": df})
  validation_result = batch.validate(suite)
  ```
- **Cách xác minh sau khi sửa:** Chạy kiểm thử thành công trả về `success=True` không kèm bất kỳ deprecation warning nào.
- **Điều học được:** Khi làm việc với các thư viện Data Engineering phát triển nhanh như Great Expectations, cần đọc trực tiếp tài liệu Migration Guide của phiên bản 1.x thay vì dựa vào các bài hướng dẫn cũ phiên bản 0.18.

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
| `retrieval_hit_rate` | **1.0000** | **0.6000** | **1.0000** | Phục hồi hoàn hảo sau khi làm sạch lại từ nguồn |
| `mean_token_f1` | **0.8965** | **0.6159** | **0.8965** | Trở về độ chính xác ban đầu |
| `judge_accuracy` | **1.0000** | **0.7000** | **1.0000** | Đánh giá đạt điểm tuyệt đối |
| Quality checks | **PASS** | **FAIL** | **PASS** | Bắt trúng lỗi truncate title và duplicate rows |
| Freshness status | **FRESH** | **FRESH** | **FRESH** | 1 bài cũ (Baseline) &rarr; 4 bài cũ (Corrupted) &rarr; 1 bài cũ (Repaired) |

### Kết luận từ số liệu:
Chốt kiểm dịch Great Expectations 1.x đã đóng vai trò người gác cổng hoàn hảo: khi dữ liệu bị tiêm lỗi, chốt kiểm dịch lập tức chuyển sang `FAIL`, giúp ngăn chặn dữ liệu hỏng thâm nhập vào các môi trường production phục vụ người dùng.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. Thành thạo công nghệ Data Observability chuẩn công nghiệp với Great Expectations 1.x Fluent API.
2. Hiểu rõ sự khác biệt giữa Data Integrity (tính toàn vẹn) và Data Freshness (tính tươi mới), và tại sao cả hai đều quan trọng đối với RAG.
3. Kỹ năng thiết kế Ingestion Pipeline có khả năng tự phục hồi (Fault Tolerance) nhờ cơ chế Offline Fallback Snapshot.

### Nếu có thêm thời gian:
Tôi sẽ bổ sung thêm các Expectation kiểm tra Semantic Drift (độ lệch phân phối ngữ nghĩa của vector embedding) bằng Great Expectations kết hợp kiểm định thống kê Kolmogorov-Smirnov.
