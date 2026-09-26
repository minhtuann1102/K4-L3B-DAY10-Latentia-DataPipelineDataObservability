from __future__ import annotations

from core.config import load_settings
from core.utils import df_to_records, now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=== Phase 1: Baseline Pipeline ===")

    settings = load_settings()

    # Step 1: Load or fetch raw records
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        print(f"Loading existing raw records from {settings.paths.raw_records_json}")
        records = load_raw_records(settings.paths.raw_records_json)
    else:
        print("Fetching source records...")
        records = fetch_source_records(settings)
    print(f"Loaded {len(records)} records.")

    # Step 2: Clean data
    run_date = now_utc()
    df = build_clean_dataframe(records, run_date)
    print(f"Clean dataframe: {len(df)} rows.")

    # Step 3: Save clean artifacts
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df_to_records(df))
    print(f"Saved clean data to {settings.paths.clean_csv}")

    # Step 4: Build ChromaDB index
    print("Building ChromaDB index (baseline)...")
    index = LocalEmbeddingIndex.build(
        df, settings, embeddings_output_path=settings.paths.embeddings_json
    )
    print(f"Index built: {len(index.documents)} documents in collection '{settings.baseline_collection_name}'.")

    # Step 5: Build or load test set
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        print(f"Using existing test set from {settings.paths.eval_testset}")
    else:
        test_set = build_test_set(df, settings.paths.eval_testset)
        print(f"Generated test set: {len(test_set)} questions.")

    # Step 6: Evaluate baseline
    print("Evaluating baseline pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"Baseline metrics: hit_rate={metrics['retrieval_hit_rate']:.4f}, token_f1={metrics['mean_token_f1']:.4f}")

    # Step 7: Run quality checks
    print("Running data quality checks...")
    quality = run_data_quality_checks(df, settings, "baseline")
    print(f"Quality check: success={quality['success']}")

    # Step 8: Freshness report
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"Freshness: is_fresh={freshness['is_fresh']}, stale_rows={freshness['stale_rows']}/{freshness['total_rows']}")

    # Step 9: Generate Phase 1 Markdown report
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "total_records": len(df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality,
        freshness=freshness,
    )
    print(f"Phase 1 report saved to {settings.paths.baseline_report}")

    print("\n=== Phase 1 Complete ===")
    print(f"  Retrieval Hit Rate : {metrics['retrieval_hit_rate']:.4f}")
    print(f"  Mean Token F1      : {metrics['mean_token_f1']:.4f}")
    print(f"  Quality Gate       : {'PASS' if quality['success'] else 'FAIL'}")
    print(f"  Freshness SLA      : {'FRESH' if freshness['is_fresh'] else 'STALE'}")
