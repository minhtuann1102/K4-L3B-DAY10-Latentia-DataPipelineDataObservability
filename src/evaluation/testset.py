from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Build a 10-question evaluation set covering 4 question types from the clean DataFrame."""
    if len(df) < 4:
        raise ValueError(f"Need at least 4 papers to build test set, got {len(df)}")

    test_set: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    def pick_row(exclude: set[str] | None = None) -> pd.Series:
        mask = ~df["paper_id"].isin(exclude or set())
        subset = df[mask]
        if subset.empty:
            subset = df
        return subset.iloc[0]

    # 3 summary questions
    for i in range(3):
        row = df.iloc[i % len(df)]
        paper_id = row["paper_id"]
        title = row["title"]
        summary = row.get("summary", "")
        ground_truth = summary[:300] if summary else title
        test_set.append(
            {
                "id": f"q_summary_{i + 1}",
                "question_type": "summary",
                "question": f"What is the paper '{title}' about?",
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        used_ids.add(paper_id)

    # 3 authors questions
    for i in range(3):
        row = df.iloc[(i + 3) % len(df)]
        paper_id = row["paper_id"]
        title = row["title"]
        authors = row.get("authors_joined", row.get("authors", ""))
        ground_truth = str(authors) if authors else "Unknown"
        test_set.append(
            {
                "id": f"q_authors_{i + 1}",
                "question_type": "authors",
                "question": f"Who authored the paper '{title}'?",
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    # 2 date questions
    for i in range(2):
        row = df.iloc[(i + 6) % len(df)]
        paper_id = row["paper_id"]
        title = row["title"]
        published = row.get("published", "")
        ground_truth = str(published)[:10] if published else "Unknown"
        test_set.append(
            {
                "id": f"q_date_{i + 1}",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    # 2 categories questions
    for i in range(2):
        row = df.iloc[(i + 8) % len(df)]
        paper_id = row["paper_id"]
        title = row["title"]
        categories = row.get("categories_joined", row.get("categories", ""))
        ground_truth = str(categories) if categories else "Unknown"
        test_set.append(
            {
                "id": f"q_categories_{i + 1}",
                "question_type": "categories",
                "question": f"What categories does the paper '{title}' belong to?",
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
