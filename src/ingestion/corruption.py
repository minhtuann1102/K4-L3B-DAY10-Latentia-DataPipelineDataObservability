from __future__ import annotations

import random
from pathlib import Path

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Simulate 6 data corruption scenarios and log each one."""
    df = df.copy()
    log: list[dict] = []
    rng = random.Random(42)

    # 1. Drop latest records (20% newest by published date)
    if "published" in df.columns and len(df) > 5:
        df_sorted = df.sort_values("published", ascending=False)
        n_drop = max(1, int(len(df) * 0.2))
        drop_ids = df_sorted.head(n_drop)["paper_id"].tolist()
        df = df[~df["paper_id"].isin(drop_ids)].reset_index(drop=True)
        log.append({
            "type": "drop_latest_records",
            "affected_rows": n_drop,
            "description": f"Dropped {n_drop} most-recent records (20% of dataset)",
        })
    else:
        log.append({"type": "drop_latest_records", "affected_rows": 0, "description": "Skipped: too few rows"})

    # 2. Blank summary (erase summary for ~3 rows)
    if "summary" in df.columns and len(df) >= 3:
        idx = rng.sample(list(df.index), min(3, len(df)))
        df.loc[idx, "summary"] = ""
        log.append({
            "type": "blank_summary",
            "affected_rows": len(idx),
            "description": f"Blanked summary field for rows: {idx}",
        })

    # 3. Inject noise into summary (~3 rows)
    if "summary" in df.columns and len(df) >= 3:
        idx = rng.sample(list(df.index), min(3, len(df)))
        noise = "###CORRUPT@@@!!!"
        df.loc[idx, "summary"] = df.loc[idx, "summary"].apply(lambda s: f"{noise} {s} {noise}")
        log.append({
            "type": "inject_noise",
            "affected_rows": len(idx),
            "description": f"Injected noise characters into summary for rows: {idx}",
        })

    # 4. Truncate title to < 8 chars (~3 rows)
    if "title" in df.columns and len(df) >= 3:
        idx = rng.sample(list(df.index), min(3, len(df)))
        df.loc[idx, "title"] = df.loc[idx, "title"].apply(lambda t: t[:6] if isinstance(t, str) and len(t) > 6 else t)
        log.append({
            "type": "truncate_title",
            "affected_rows": len(idx),
            "description": f"Truncated title to <8 chars for rows: {idx}",
        })

    # 5. Stale date: push published date back 2 years (~3 rows)
    if "published" in df.columns and len(df) >= 3:
        idx = rng.sample(list(df.index), min(3, len(df)))
        two_years = pd.Timedelta(days=730)
        df.loc[idx, "published"] = df.loc[idx, "published"] - two_years
        if "age_days" in df.columns:
            df.loc[idx, "age_days"] = df.loc[idx, "age_days"] + 730
        log.append({
            "type": "stale_date",
            "affected_rows": len(idx),
            "description": f"Set published date 2 years in the past for rows: {idx}",
        })

    # 6. Duplicate rows (clone 3 rows with modified paper_id)
    if len(df) >= 3:
        idx = rng.sample(list(df.index), min(3, len(df)))
        duplicates = df.loc[idx].copy()
        duplicates["paper_id"] = duplicates["paper_id"].apply(lambda pid: f"{pid}_dup")
        df = pd.concat([df, duplicates], ignore_index=True)
        log.append({
            "type": "duplicate_rows",
            "affected_rows": len(idx),
            "description": f"Duplicated {len(idx)} rows with modified paper_id suffix '_dup'",
        })

    # Rebuild text_for_embedding for all rows
    def _rebuild_embedding_text(row: pd.Series) -> str:
        published_str = ""
        if "published" in row and pd.notna(row["published"]):
            try:
                published_str = pd.Timestamp(row["published"]).strftime("%Y-%m-%d")
            except Exception:
                published_str = str(row["published"])[:10]
        return (
            f"Title: {row.get('title', '')}\n"
            f"Authors: {row.get('authors', '')}\n"
            f"Published: {published_str}\n"
            f"Categories: {row.get('categories', '')}\n"
            f"Summary: {row.get('summary', '')}"
        )

    df["text_for_embedding"] = df.apply(_rebuild_embedding_text, axis=1)

    write_json(Path(output_log_path), log)
    return df
