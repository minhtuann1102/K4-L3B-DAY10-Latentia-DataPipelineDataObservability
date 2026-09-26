# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG
**Team Latentia — Khóa 4 Lớp B (VinUni AI Engineering Lab)**

> **Mục tiêu cốt lõi:** Xây dựng Data Pipeline hoàn chỉnh cho hệ thống RAG Agent, tích hợp Data Observability (Great Expectations 1.x + Freshness SLA), đo lường mức độ suy thoái ngầm khi dữ liệu bị lỗi (Silent Failure via Synthetic Data Corruption) và chứng minh năng lực tự phục hồi bất biến (Idempotent Self-Repair).

---

## 👥 Thành viên nhóm Latentia

| STT | Họ và tên | MSSV | Vai trò chính | Báo cáo cá nhân |
|---:|---|---|---|---|
| 1 | **Nguyễn Minh Tuấn** | `2A202602420` | **Techlead & Pipeline Integrator** (`core/`, `pipelines/`, `script/`, `demo_hub.py`) | [Báo cáo cá nhân](report/2A202602420_NguyenMinhTuan.md) |
| 2 | **Nguyễn Minh Thắng** | `2A202602706` | **Data Foundation & Quality Gate** (`crossref.py`, `cleaning.py`, `quality.py`) | [Báo cáo cá nhân](report/2A202602706_NguyenMinhThang.md) |
| 3 | **Nguyễn Thị Vàng** | `2A202602897` | **RAG, Vector Index & Benchmark** (`embeddings.py`, `index.py`, `testset.py`, `corruption.py`) | [Báo cáo cá nhân](report/2A202602897_NguyenThiVang.md) |

- **Báo cáo tổng kết nhóm:** [report/group_report.md](report/group_report.md)
- **Danh sách phân công chi tiết:** [docs/TEAM.md](docs/TEAM.md)

---

## 📊 Kết Quả Đối Chiếu 3 Trạng Thái (Thực Nghiệm Tự Động)

*(Trích xuất từ báo cáo chính thức tại [data/reports/corruption_report.md](data/reports/corruption_report.md))*

| Chỉ số quan sát | Baseline (Chuẩn) | Corrupted (Lỗi) | Repaired (Phục hồi) | Nhận xét thực nghiệm |
| :--- | :---: | :---: | :---: | :--- |
| **`retrieval_hit_rate`** | **1.0000 (100%)** | **0.6000 (60.0%)** | **1.0000 (100%)** | 📉 Tụt 40% (Silent Failure) &rarr; ✅ Phục hồi 100% |
| **`mean_token_f1`** | **0.8965 (89.7%)** | **0.6159 (61.6%)** | **0.8965 (89.7%)** | Chất lượng câu trả lời khôi phục chuẩn xác |
| **`judge_accuracy`** | **1.0000 (100%)** | **0.7000 (70.0%)** | **1.0000 (100%)** | LLM-as-a-judge đánh giá chính xác |
| **`GX Quality Gate`** | **PASS** | ❌ **FAIL** | ✅ **PASS** | Great Expectations 1.x bắt trúng vi phạm |
| **`Freshness SLA`** | **FRESH** | **FRESH** | **FRESH** | Đảm bảo tỷ lệ bài quá 180 ngày &le; 25% |
| **Tổng số bản ghi** | 24 dòng | 23 dòng (-1) | 24 dòng | Phục hồi nguyên vẹn từ Snapshot gốc |

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Demo

### 1. Kích hoạt môi trường ảo
```bash
# Trên Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Cài đặt gói ở chế độ editable
python -m pip install -e .
```

### 2. Thực thi Pipeline bằng dòng lệnh (CLI)
```bash
# 1. Chạy Pha Chuẩn (Baseline Pipeline): exit code 0
python script/run_phase1.py

# 2. Chạy Luồng Tiêm Lỗi & Tự Phục Hồi (Corruption & Repair Flow): exit code 0
python script/run_corruption_flow.py
```

### 3. Khởi động Web Demo & Presentation Hub (Vừa Thuyết Trình Vừa Live Demo)
```bash
# Khởi động server demo cục bộ
python script/demo_hub.py
```
👉 Mở trình duyệt tại **`http://localhost:8501`** (hoặc mở trực tiếp file [`docs/demo_hub.html`](docs/demo_hub.html)).
- **Chế độ Thuyết trình:** 8 Slide tương tác cao cấp (hỗ trợ phím mũi tên, fullscreen `F`, speaker notes `N`).
- **Chế độ Kết hợp (Split):** Nửa bên trái là Slide, nửa bên phải là Console chạy script thật và kiểm thử RAG query thời gian thực!

---

## 🏗️ Cấu Trúc Repository

```text
K4-L3B-DAY10-Latentia-DataPipelineDataObservability/
├── data/
│   ├── raw/              ← crossref_response.json, crossref_records.json
│   ├── clean/            ← papers_clean.csv, papers_clean.json
│   ├── eval/             ← test_set.json (10 câu benchmark)
│   ├── quality/          ← baseline/corrupted/freshness quality reports (GX 1.x)
│   ├── results/          ← baseline/corrupted/repaired_metrics.json, corruption_log.json
│   └── reports/          ← phase1_report.md, corruption_report.md
├── script/
│   ├── run_phase1.py            ← Entrypoint chạy Phase 1
│   ├── run_corruption_flow.py   ← Entrypoint chạy Corruption & Repair
│   └── demo_hub.py              ← Backend server phục vụ Live Demo Hub
├── src/
│   ├── core/             ← config.py, utils.py
│   ├── ingestion/        ← crossref.py, cleaning.py, corruption.py
│   ├── retrieval/        ← embeddings.py (retry backoff), index.py, qa.py
│   ├── evaluation/       ← metrics.py, testset.py
│   └── observability/    ← quality.py (GX 1.x Fluent API), reporting.py
├── docs/
│   ├── slides.html       ← Bộ slide thuyết trình HTML tương tác
│   ├── SLIDES.md         ← Bản slide Markdown đọc nhanh
│   ├── demo_hub.html     ← Web Hub Live Demo & Presentation
│   ├── CHECKPOINTS.md    ← Bảng phân bổ 6 checkpoints của bài lab
│   ├── RUBRIC.md         ← Tiêu chí nghiệm thu 100 điểm
│   ├── SUBMISSION.md     ← Quy định nộp bài & checklist
│   └── TEAM.md           ← Phân công chi tiết nhóm Latentia
├── report/
│   ├── group_report.md   ← Báo cáo tổng kết toàn diện của nhóm Latentia
│   ├── 2A202602420_NguyenMinhTuan.md  ← Báo cáo cá nhân: Nguyễn Minh Tuấn
│   ├── 2A202602706_NguyenMinhThang.md ← Báo cáo cá nhân: Nguyễn Minh Thắng
│   └── 2A202602897_NguyenThiVang.md   ← Báo cáo cá nhân: Nguyễn Thị Vàng
└── README.md
```

---

## 🛡️ Kiểm Tra An Toàn & Bảo Mật

- [x] **File `.env`:** Đã cấu hình chặn trong `.gitignore`, không bao giờ được commit lên Git.
- [x] **Môi trường ảo & Cache:** Đã loại trừ `.venv/`, `__pycache__/`, `*.pyc`.
- [x] **Cơ sở dữ liệu Vector tạm:** Đã chặn `data/chroma/`, `chroma_db/`, `*.sqlite3`.
- [x] **Quét khóa bí mật:** Không có bất kỳ API Key (`GOOGLE_API_KEY`, `OPENAI_API_KEY`) hay secret token nào trong source code hay reports.
