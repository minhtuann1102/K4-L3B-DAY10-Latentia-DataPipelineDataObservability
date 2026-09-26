# Data Corruption & Repair Report

> Generated: 2026-09-26 05:03 UTC

---

## 1. Pipeline States Overview

This report compares three states of the RAG pipeline:

- **Baseline**: Clean data, full corpus
- **Corrupted**: 6 synthetic corruption scenarios injected
- **Repaired**: Corpus restored from raw source, idempotent repair

---

## 2. Retrieval & Evaluation Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Samples | 10 | 10 | 10 |
| Retrieval Hit Rate | 1.0000 (100.0%) | 0.6000 (60.0%) | 1.0000 (100.0%) |
| Mean Token F1 | 0.8965 (89.7%) | 0.6159 (61.6%) | 0.8965 (89.7%) |
| Judge Accuracy | 1.0000 (100.0%) | 0.7000 (70.0%) | 1.0000 (100.0%) |

---

## 3. Impact Analysis

| Transition | Hit Rate Delta | Observation |
|---|---|---|
| Baseline → Corrupted | -0.4000 (-40.0%) | 📉 Degradation detected (Silent Failure) |
| Baseline → Repaired | +0.0000 (+0.0%) | ✅ Recovery confirmed |

---

## 4. Data Quality Gate Results

| Check | Corrupted | Repaired |
|---|---|---|
| GX Suite Result | ❌ FAIL | ✅ PASS |
| Row Count | 23 | 24 |

---

## 5. Freshness SLA

| Field | Corrupted | Repaired |
|---|---|---|
| Is Fresh | ✅ | ✅ FRESH |
| Stale Rows | 4 / 23 | 1 / 24 |

---

## 6. Conclusion

The corruption suite successfully demonstrated **Silent Failure** — RAG pipeline quality degraded
without explicit error when data was corrupted. The **Idempotent Repair** mechanism restored
data from the original raw snapshot, bringing metrics back to near-baseline levels.

*Report generated automatically by Latentia Data Pipeline.*
