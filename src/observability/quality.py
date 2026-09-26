from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run Great Expectations 1.x ephemeral quality checks on the given DataFrame."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(gx.ExpectationSuite(name="papers_suite"))

    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=1, max_value=200)
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id")
    )
    if "summary" in df.columns:
        suite.add_expectation(
            gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=1)
        )

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="papers_validation",
            data=batch_def,
            suite=suite,
        )
    )
    results = validation_definition.run(batch_parameters={"dataframe": df})

    success = bool(results.success)
    expectations_results = []
    for result in results.results:
        expectations_results.append(
            {
                "expectation_type": result.expectation_config.type,
                "success": bool(result.success),
                "kwargs": result.expectation_config.kwargs,
            }
        )

    payload = {
        "success": success,
        "report_name": report_name,
        "row_count": len(df),
        "expectations": expectations_results,
        "statistics": {
            "evaluated_expectations": len(expectations_results),
            "successful_expectations": sum(1 for e in expectations_results if e["success"]),
            "unsuccessful_expectations": sum(1 for e in expectations_results if not e["success"]),
        },
    }

    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    ensure_parent(report_path)
    write_json(report_path, payload)

    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Build Freshness SLA report: warn if >25% of papers are older than threshold_days."""
    threshold = settings.freshness_threshold_days
    total_rows = len(df)

    if "age_days" in df.columns and total_rows > 0:
        stale_count = int((df["age_days"] > threshold).sum())
        stale_ratio = stale_count / total_rows
        is_fresh = stale_ratio <= 0.25
    else:
        stale_count = 0
        stale_ratio = 0.0
        is_fresh = True

    latest_published = ""
    oldest_published = ""
    if "published" in df.columns:
        valid_dates = df["published"].dropna()
        if len(valid_dates) > 0:
            latest_published = str(valid_dates.max())
            oldest_published = str(valid_dates.min())

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_count,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    ensure_parent(Path(report_path))
    write_json(Path(report_path), payload)

    return payload
