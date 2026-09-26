from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import df_to_records, now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== Corruption & Repair Flow ===")

    settings = load_settings()

    # Step 1: Load clean baseline DataFrame and baseline metrics
    if not settings.paths.clean_json.exists():
        raise RuntimeError(
            f"Clean data not found at {settings.paths.clean_json}. Run run_phase1.py first."
        )
    if not settings.paths.baseline_metrics.exists():
        raise RuntimeError(
            f"Baseline metrics not found at {settings.paths.baseline_metrics}. Run run_phase1.py first."
        )
    if not settings.paths.eval_testset.exists():
        raise RuntimeError(
            f"Test set not found at {settings.paths.eval_testset}. Run run_phase1.py first."
        )

    clean_records = read_json(settings.paths.clean_json)
    df_clean = pd.DataFrame(clean_records)
    # Restore proper dtypes after JSON round-trip
    if "published" in df_clean.columns:
        df_clean["published"] = pd.to_datetime(df_clean["published"], utc=True, errors="coerce")
    if "age_days" in df_clean.columns:
        df_clean["age_days"] = pd.to_numeric(df_clean["age_days"], errors="coerce").fillna(0).astype(int)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"Loaded clean data: {len(df_clean)} rows, baseline hit_rate={baseline_metrics['retrieval_hit_rate']:.4f}")

    # Step 2: Corrupt the clean DataFrame
    print("Injecting 6 corruption scenarios...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    print(f"Corrupted DataFrame: {len(df_corrupted)} rows. Log saved to {settings.paths.corruption_log}")

    # Step 3: Save corrupted artifacts
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, df_to_records(df_corrupted))

    # Step 4: Build corrupted ChromaDB index and evaluate
    print("Building corrupted index and evaluating...")
    corrupted_index = LocalEmbeddingIndex.build(
        df_corrupted, settings, embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"Corrupted metrics: hit_rate={corrupted_metrics['retrieval_hit_rate']:.4f}, token_f1={corrupted_metrics['mean_token_f1']:.4f}")

    # Step 5: Quality & Freshness on corrupted data
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.corrupted_quality_report)
    print(f"Corrupted quality: success={corrupted_quality['success']}, is_fresh={corrupted_freshness['is_fresh']}")

    # Step 6: Idempotent Repair — rebuild from raw records
    print("Repairing from raw records (idempotent)...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    run_date = now_utc()
    df_repaired = build_clean_dataframe(raw_records, run_date)
    print(f"Repaired DataFrame: {len(df_repaired)} rows.")

    # Step 7: Save repaired artifacts
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df_to_records(df_repaired))

    # Step 8: Build repaired index and evaluate
    print("Building repaired index and evaluating...")
    repaired_index = LocalEmbeddingIndex.build(
        df_repaired, settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    print(f"Repaired metrics: hit_rate={repaired_metrics['retrieval_hit_rate']:.4f}, token_f1={repaired_metrics['mean_token_f1']:.4f}")

    # Step 9: Quality & Freshness on repaired data
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.freshness_report)
    print(f"Repaired quality: success={repaired_quality['success']}, is_fresh={repaired_freshness['is_fresh']}")

    # Step 10: Generate corruption comparison report
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"Corruption report saved to {settings.paths.comparison_report}")

    # Summary table
    print("\n=== 3-State Comparison ===")
    print(f"{'Metric':<25} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}")
    print("-" * 58)
    print(f"{'Retrieval Hit Rate':<25} {baseline_metrics['retrieval_hit_rate']:>10.4f} {corrupted_metrics['retrieval_hit_rate']:>10.4f} {repaired_metrics['retrieval_hit_rate']:>10.4f}")
    print(f"{'Mean Token F1':<25} {baseline_metrics['mean_token_f1']:>10.4f} {corrupted_metrics['mean_token_f1']:>10.4f} {repaired_metrics['mean_token_f1']:>10.4f}")
    print(f"{'Judge Accuracy':<25} {baseline_metrics.get('judge_accuracy', 0):>10.4f} {corrupted_metrics.get('judge_accuracy', 0):>10.4f} {repaired_metrics.get('judge_accuracy', 0):>10.4f}")
    print("\n=== Corruption Flow Complete ===")
