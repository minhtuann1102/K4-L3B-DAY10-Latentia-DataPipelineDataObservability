from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

import pandas as pd

from ingestion.crossref import PaperRecord


def normalize_text(value: Any) -> str:
    """Normalize whitespace in text fields and join collections."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = ", ".join(normalize_text(item) for item in value if item is not None and str(item).strip())
    return " ".join(str(value).split())


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Convert raw PaperRecord objects into a clean pandas DataFrame.

    Steps:
    1. Convert records into dictionaries.
    2. Normalize textual fields (whitespace, clean strings).
    3. Normalize published/updated date to UTC datetime.
    4. Calculate age_days relative to run_date.
    5. Create helper columns (authors_joined, categories_joined, summary_chars, text_for_embedding).
    6. Deduplicate by paper_id and reset index.
    """
    if not records:
        return pd.DataFrame()

    rows = []
    for record in records:
        if hasattr(record, "model_dump"):
            row = record.model_dump()
        elif hasattr(record, "__dict__"):
            row = asdict(record) if hasattr(record, "__dataclass_fields__") else vars(record).copy()
        elif isinstance(record, dict):
            row = record.copy()
        else:
            row = dict(record)
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Normalize text fields
    for col in ["paper_id", "title", "summary", "primary_category", "comment", "abs_url", "pdf_url"]:
        if col in df.columns:
            df[col] = df[col].apply(normalize_text)

    # Authors & Categories normalization
    if "authors" in df.columns:
        df["authors"] = df["authors"].apply(normalize_text)
        df["authors_joined"] = df["authors"]

    if "categories" in df.columns:
        df["categories"] = df["categories"].apply(normalize_text)
        df["categories_joined"] = df["categories"]

    if "summary" in df.columns:
        df["summary_chars"] = df["summary"].str.len()

    # Normalize published and updated dates
    if "published" in df.columns:
        df["published"] = pd.to_datetime(df["published"], utc=True, errors="coerce")

    if "updated" in df.columns:
        df["updated"] = pd.to_datetime(df["updated"], utc=True, errors="coerce")

    # Ensure run_date is UTC-compatible Timestamp
    run_ts = pd.Timestamp(run_date)
    if run_ts.tzinfo is None:
        run_ts = run_ts.tz_localize("UTC")
    else:
        run_ts = run_ts.tz_convert("UTC")

    # Calculate age_days
    if "published" in df.columns:
        df["age_days"] = (run_ts - df["published"]).dt.days

    # Build embedding document text
    def _build_embedding_text(row: pd.Series) -> str:
        published_str = (
            row["published"].strftime("%Y-%m-%d")
            if "published" in row and pd.notna(row["published"])
            else ""
        )
        title_str = row.get("title", "")
        authors_str = row.get("authors", "")
        categories_str = row.get("categories", "")
        summary_str = row.get("summary", "")

        return (
            f"Title: {title_str}\n"
            f"Authors: {authors_str}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_str}\n"
            f"Summary: {summary_str}"
        )

    df["text_for_embedding"] = df.apply(_build_embedding_text, axis=1)

    # Deduplicate by paper_id (unique key)
    if "paper_id" in df.columns:
        df = df.drop_duplicates(subset=["paper_id"], keep="first")

    return df.reset_index(drop=True)
