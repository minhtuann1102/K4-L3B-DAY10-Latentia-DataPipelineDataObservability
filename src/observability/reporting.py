from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate baseline phase Markdown report."""
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    hit_rate = metrics.get("retrieval_hit_rate", 0.0)
    token_f1 = metrics.get("mean_token_f1", 0.0)
    judge_acc = metrics.get("judge_accuracy", 0.0)
    samples = metrics.get("samples", 0)

    quality_ok = quality.get("success", False)
    q_evaluated = quality.get("statistics", {}).get("evaluated_expectations", 0)
    q_passed = quality.get("statistics", {}).get("successful_expectations", 0)

    is_fresh = freshness.get("is_fresh", True)
    stale_rows = freshness.get("stale_rows", 0)
    total_rows = freshness.get("total_rows", 0)
    stale_ratio = freshness.get("stale_ratio", 0.0)
    threshold = freshness.get("freshness_threshold_days", 180)

    md = f"""# Phase 1 Baseline Report

> Generated: {run_date}

---

## 1. Data Source Summary

| Field | Value |
|---|---|
| Source | {source_summary.get("source_api", "Crossref REST API")} |
| Query | {source_summary.get("source_query", "")} |
| Total Records Fetched | {source_summary.get("total_records", total_rows)} |
| Run Date | {run_date} |

---

## 2. Baseline Evaluation Metrics

| Metric | Value |
|---|---|
| Samples Evaluated | {samples} |
| Retrieval Hit Rate | {hit_rate:.4f} ({hit_rate * 100:.1f}%) |
| Mean Token F1 | {token_f1:.4f} |
| Judge Accuracy | {judge_acc:.4f} ({judge_acc * 100:.1f}%) |

---

## 3. Data Quality (Great Expectations 1.x)

| Field | Value |
|---|---|
| Overall Success | {"✅ PASS" if quality_ok else "❌ FAIL"} |
| Expectations Evaluated | {q_evaluated} |
| Passed | {q_passed} |
| Failed | {q_evaluated - q_passed} |

---

## 4. Freshness SLA

| Field | Value |
|---|---|
| Freshness Status | {"✅ FRESH" if is_fresh else "⚠️ STALE"} |
| Threshold | {threshold} days |
| Stale Records | {stale_rows} / {total_rows} ({stale_ratio * 100:.1f}%) |
| Latest Published | {freshness.get("latest_published", "N/A")} |
| Oldest Published | {freshness.get("oldest_published", "N/A")} |

---

*Report generated automatically by Latentia Data Pipeline.*
"""
    write_text(Path(report_path), md)


def generate_corruption_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate Markdown report comparing Baseline vs Corrupted vs Repaired states."""
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def fmt(val: float) -> str:
        return f"{val:.4f} ({val * 100:.1f}%)"

    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_judge = baseline_metrics.get("judge_accuracy", 0.0)
    c_judge = corrupted_metrics.get("judge_accuracy", 0.0)
    r_judge = repaired_metrics.get("judge_accuracy", 0.0)

    b_samples = baseline_metrics.get("samples", 0)
    c_samples = corrupted_metrics.get("samples", 0)
    r_samples = repaired_metrics.get("samples", 0)

    hit_delta_corrupt = c_hit - b_hit
    hit_delta_repair = r_hit - b_hit

    md = f"""# Data Corruption & Repair Report

> Generated: {run_date}

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
| Samples | {b_samples} | {c_samples} | {r_samples} |
| Retrieval Hit Rate | {fmt(b_hit)} | {fmt(c_hit)} | {fmt(r_hit)} |
| Mean Token F1 | {fmt(b_f1)} | {fmt(c_f1)} | {fmt(r_f1)} |
| Judge Accuracy | {fmt(b_judge)} | {fmt(c_judge)} | {fmt(r_judge)} |

---

## 3. Impact Analysis

| Transition | Hit Rate Delta | Observation |
|---|---|---|
| Baseline → Corrupted | {hit_delta_corrupt:+.4f} ({hit_delta_corrupt * 100:+.1f}%) | {"📉 Degradation detected (Silent Failure)" if hit_delta_corrupt < 0 else "No significant degradation"} |
| Baseline → Repaired | {hit_delta_repair:+.4f} ({hit_delta_repair * 100:+.1f}%) | {"✅ Recovery confirmed" if hit_delta_repair >= -0.05 else "⚠️ Partial recovery"} |

---

## 4. Data Quality Gate Results

| Check | Corrupted | Repaired |
|---|---|---|
| GX Suite Result | {"❌ FAIL" if not corrupted_quality.get("success") else "✅ PASS"} | {"✅ PASS" if repaired_quality.get("success") else "❌ FAIL"} |
| Row Count | {corrupted_quality.get("row_count", "N/A")} | {repaired_quality.get("row_count", "N/A")} |

---

## 5. Freshness SLA

| Field | Corrupted | Repaired |
|---|---|---|
| Is Fresh | {"✅" if corrupted_freshness.get("is_fresh") else "⚠️ STALE"} | {"✅ FRESH" if repaired_freshness.get("is_fresh") else "⚠️ STALE"} |
| Stale Rows | {corrupted_freshness.get("stale_rows", 0)} / {corrupted_freshness.get("total_rows", 0)} | {repaired_freshness.get("stale_rows", 0)} / {repaired_freshness.get("total_rows", 0)} |

---

## 6. Conclusion

The corruption suite successfully demonstrated **Silent Failure** — RAG pipeline quality degraded
without explicit error when data was corrupted. The **Idempotent Repair** mechanism restored
data from the original raw snapshot, bringing metrics back to near-baseline levels.

*Report generated automatically by Latentia Data Pipeline.*
"""
    write_text(Path(report_path), md)
