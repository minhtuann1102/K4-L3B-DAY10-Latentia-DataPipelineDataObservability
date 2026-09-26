# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo vai trò cá nhân: Nguyễn Minh Tuấn (Techlead & Pipeline Integrator).

---

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên          | Nguyễn Minh Tuấn           |
| MSSV               | 2A202602420                |
| Khóa/Lớp           | K4-L3B                     |
| Tên nhóm           | Latentia                   |
| Vai trò chính      | Techlead & Pipeline Integrator (`core/`, `pipelines/`, `script/`, `demo_hub.py`) |
| Repository         | https://github.com/minhtuann1102/K4-L3B-DAY10-Latentia-DataPipelineDataObservability |
| Ngày hoàn thành    | 2026-09-26                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| **Pipeline Orchestration Phase 1** | `src/pipelines/phase1.py`, `script/run_phase1.py` | Cấu hình `Settings`, raw data records | Clean dataset, baseline ChromaDB collection, `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| **Corruption & Repair Flow** | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Clean data, raw snapshot | `corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Hoàn thành |
| **Core Config & Utilities** | `src/core/config.py`, `src/core/utils.py` | Biến môi trường `.env`, paths | Dataclass `Settings`, `Paths`, hàm đọc/ghi JSON/CSV an toàn | Hoàn thành |
| **Interactive Demo & Presentation Hub** | `script/demo_hub.py`, `docs/demo_hub.html`, `docs/slides.html` | Artifacts kết quả, script pipeline | Giao diện điều khiển Live Demo & 8 slide thuyết trình trực quan | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| --------- | ----------------------------- | --------------------- |
| **Quản trị Git & Bảo mật Repository** | Toàn đội (Thắng, Vàng) | Loại trừ triệt để `.env`, `chroma/`, `.venv/` khỏi Git; đảm bảo 100% thành viên có commit trên `main` |
| **Hỗ trợ Debug Great Expectations 1.x** | Nguyễn Minh Thắng (`quality.py`) | Tích hợp thành công Ephemeral Context của GX 1.x vào pipeline end-to-end mà không làm chậm luồng |
| **Tối ưu hóa Resilience cho Vector Index** | Nguyễn Thị Vàng (`embeddings.py`) | Bổ sung cơ chế Retry Exponential Backoff cho các cuộc gọi API embedding để chống gián đoạn mạng Wi-Fi |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết kế luồng Phase 1 Baseline | `src/pipelines/phase1.py` | Tự động hóa từ Ingestion &rarr; Clean &rarr; GX Gate &rarr; ChromaDB &rarr; Benchmark | `python script/run_phase1.py` (Exit Code 0) |
| Thiết kế luồng Corruption & Repair | `src/pipelines/corruption_flow.py` | Đo lường Silent Failure và kích hoạt Idempotent Self-Repair | `python script/run_corruption_flow.py` (Exit Code 0) |
| Tự động xuất báo cáo 3 trạng thái | `src/observability/reporting.py` | Sinh bảng so sánh định lượng đa chiều Baseline vs Corrupted vs Repaired | File [data/reports/corruption_report.md](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/data/reports/corruption_report.md) |
| Xây dựng Live Demo Hub | `script/demo_hub.py`, `docs/demo_hub.html` | Giao diện web chạy kịch bản thật, stream logs và truy vấn RAG trực tiếp | Mở `http://localhost:8501` |

Output cụ thể: File báo cáo [data/reports/corruption_report.md](file:///c:/Users/NITRO/ProjectLab1/K4-L3B-DAY10-Latentia-DataPipelineDataObservability/data/reports/corruption_report.md) ghi nhận chính xác `retrieval_hit_rate` tụt từ 1.0 xuống 0.6 khi lỗi và phục hồi về đúng 1.0 sau khi chạy Repair.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống RAG cần một "nhạc trưởng" (Orchestrator) liên kết chặt chẽ các module độc lập: từ tải dữ liệu thô, làm sạch, chốt kiểm dịch chất lượng Great Expectations, lập chỉ mục vector ChromaDB đến tính toán điểm số Benchmark. Đồng thời, khi dữ liệu bị lỗi, hệ thống phải tự động điều phối quá trình tiêm lỗi, đo lường sự cố và kích hoạt phục hồi mà không gây lỗi phân mảnh trạng thái (State drift).

### Cách triển khai
1. **Quản lý cấu hình tập trung:** Sử dụng Dataclass `Settings` và `Paths` trong `src/core/config.py`, xác định rõ đường dẫn tuyệt đối/tương đối cho toàn bộ 24 artifacts của hệ sinh thái dữ liệu.
2. **Orchestration có kiểm soát lỗi:** Trong `src/pipelines/phase1.py`, thiết lập thứ tự chạy tuần tự có kiểm tra điều kiện tiên quyết: nếu dữ liệu sạch không thỏa mãn Quality Gate thì dừng ngay trước khi nạp vào Vector Database.
3. **Cơ chế Idempotent Repair Flow:** Trong `src/pipelines/corruption_flow.py`, luồng phục hồi không sửa đè trực tiếp trên dữ liệu bẩn mà xóa sạch collection cũ và nạp lại từ nguồn Raw Snapshot bất biến (`crossref_records.json`).

### Input, Output và Contract

| Thành phần | Mô tả |
| :--- | :--- |
| Input | `Settings` cấu hình, `data/raw/crossref_records.json` |
| Output | `data/results/*_metrics.json`, `data/reports/corruption_report.md` |
| Module phụ thuộc | `ingestion`, `observability`, `retrieval`, `evaluation` |
| Module sử dụng output | Giảng viên chấm thi, Web Demo Hub, CI/CD Pipeline |
| Xử lý lỗi | Thêm cơ chế retry cho HTTP calls, bọc try-except khi quản lý ChromaDB collections |

### Cách xác minh thực tế

```bash
# Xác minh Baseline Pipeline
python script/run_phase1.py
# Kết quả mong đợi: Console in ra "Phase 1 Complete", Hit Rate: 1.0000, Quality Gate: PASS, Exit Code 0.

# Xác minh Corruption & Repair Flow
python script/run_corruption_flow.py
# Kết quả mong đợi: Console in ra bảng so sánh 3 trạng thái, Exit Code 0.
```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Làm thế nào để phục hồi dữ liệu khi chốt kiểm dịch báo động `FAIL`?
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (In-place Patching):* Viết hàm rà soát trên bảng dữ liệu bị lỗi, tìm các giá trị null hay rác và vá lỗi cục bộ.
  - *Phương án 2 (Idempotent Re-creation từ Raw Snapshot):* Giữ nguyên Raw Data bất biến. Khi có sự cố, xóa bỏ toàn bộ dữ liệu tạm và index bị lỗi, chạy lại quy trình làm sạch từ đầu dựa trên Raw Snapshot gốc.
- **Phương án đã chọn:** Phương án 2 (Idempotent Re-creation).
- **Lý do:** Trong Data Engineering, việc vá lỗi cục bộ (in-place patching) rất dễ để lại các vector "ma" (Ghost Vectors) hoặc dữ liệu mâu thuẫn ngầm. Tái tạo từ nguồn Raw đáng tin cậy đảm bảo tính toán bất biến (Idempotent), kết quả hoàn toàn đồng nhất dù chạy lại bao nhiêu lần.
- **Bằng chứng:** Sau khi chạy Repair, `retrieval_hit_rate` và `mean_token_f1` phục hồi 100% khớp tuyệt đối với số liệu của Baseline ban đầu.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Khi chạy thử nghiệm `run_corruption_flow.py`, chương trình gặp lỗi:
  `httpcore.ConnectError: [Errno 11001] getaddrinfo failed` tại tầng embedding của Google GenAI.
- **Nguyên nhân gốc:** Wi-Fi giảng đường bị rớt gói tin hoặc timeout DNS đột ngột khi gửi mảng văn bản lớn lên API.
- **Cách xử lý:** Bổ sung khối vòng lặp `for attempt in range(5)` với thời gian nghỉ theo cấp số nhân `time.sleep(1.5 * (attempt + 1))` trong hàm `embed_documents` và `embed_query` tại `src/retrieval/embeddings.py`.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_corruption_flow.py`, pipeline vượt qua 100% mà không bị đứt đoạn, exit code 0.
- **Điều học được:** Mọi cuộc gọi mạng ra bên ngoài (External APIs) trong Data Pipeline bắt buộc phải có cơ chế retry with backoff và graceful degradation.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Ingestion API lấy metadata thô &rarr; lưu Snapshot `crossref_records.json` &rarr; làm sạch, khử trùng lặp và tính `text_for_embedding` &rarr; kiểm tra qua Great Expectations 1.x &rarr; Vector hóa bằng mô hình embedding &rarr; nạp vào collection ChromaDB.
2. **Evaluation set và ground-truth document IDs:** Bộ test set gồm 10 câu hỏi có kèm danh sách `ground_truth_doc_ids`. Khi RAG truy vấn, hệ thống kiểm tra xem ID của các tài liệu trích xuất được (Top-k) có chứa ground-truth ID hay không để tính Hit Rate, và tính Token F1 giữa câu trả lời sinh ra với câu trả lời chuẩn.
3. **Quality checks vs Freshness monitoring:** Quality checks (GX 1.x) kiểm tra tính đúng đắn cấu trúc dữ liệu (số dòng, not-null, unique, độ dài ký tự). Freshness monitoring kiểm tra tính hợp thời (SLA thời gian: tài liệu có bị quá cũ so với ngưỡng 180 ngày hay không).
4. **Vì sao dùng cùng test set cho 3 trạng thái:** Để đảm bảo tính chuẩn tắc của phương pháp thực nghiệm có đối chứng. Khi cố định câu hỏi và đáp án, mọi sự thay đổi điểm số hoàn toàn do chất lượng dữ liệu quyết định.
5. **Repair được xem là thành công khi:** Quality Gate chuyển từ `FAIL` về `PASS`, `retrieval_hit_rate` phục hồi từ 0.6000 về 1.0000, và báo cáo `corruption_report.md` xác nhận độ lệch delta = 0.0000 so với baseline.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | **1.0000** | **0.6000** | **1.0000** | Giảm 40% do mất tóm tắt và dính chuỗi rác; phục hồi 100% |
| `mean_token_f1` | **0.8965** | **0.6159** | **0.8965** | Câu trả lời bị giảm chất lượng rõ rệt khi context bị tiêm nhiễu |
| `judge_accuracy` | **1.0000** | **0.7000** | **1.0000** | LLM-as-a-judge nhận diện chính xác câu trả lời sai lệch |
| `mean_judge_score` | **1.0000** | **0.7000** | **1.0000** | Điểm số trung bình phục hồi về mức tối đa |
| Quality checks | **PASS** | **FAIL** | **PASS** | Great Expectations 1.x bắt lỗi chuẩn xác |
| Freshness status | **FRESH** | **FRESH** | **FRESH** | 1 stale row ở baseline, tăng lên 4 ở corrupted, về lại 1 |

### Kết luận từ số liệu:
1. `Blank summary & Truncate title` &rarr; `GX Quality Gate FAIL` &rarr; `Retrieval Hit Rate tụt 40%` (Minh chứng rõ ràng cho hiểm họa Silent Failure).
2. `Idempotent Repair từ Raw Snapshot` &rarr; `GX Quality Gate PASS` &rarr; `Toàn bộ Metrics phục hồi nguyên vẹn 100%`.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất:
1. Hiểu sâu sắc tầm quan trọng của Data Observability: Không có chốt kiểm dịch chất lượng dữ liệu, AI Agent sẽ âm thầm đưa ra quyết định sai lầm mà lập trình viên không hề hay biết.
2. Nắm vững tư duy thiết kế Idempotent Pipeline: Đảm bảo tính lặp lại (Reproducibility) và khả năng tự phục hồi mà không phát sinh tác dụng phụ.
3. Kỹ năng điều phối dự án: Phân chia module rõ ràng, thiết lập Data Contract giữa các thành viên giúp việc tích hợp mã nguồn diễn ra nhanh chóng và không xảy ra xung đột.

### Nếu có thêm thời gian:
Nhóm sẽ tích hợp cơ chế tự động gửi cảnh báo qua Webhook (Slack / Discord / Telegram) ngay khi Great Expectations phát hiện vi phạm, đồng thời lưu trữ lineage dữ liệu lên OpenLineage / Marquez.
