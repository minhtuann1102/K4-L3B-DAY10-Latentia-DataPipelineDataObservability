from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import urlencode

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_html_tags(text: str) -> str:
    """Remove HTML/XML tags like <jats:p> from text."""
    if not text:
        return ""
    # Remove <jats:p>...</jats:p> tags and content inside
    text = re.sub(r'<jats:p[^>]*>', '', text)
    text = re.sub(r'</jats:p>', '', text)
    # Remove any other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _format_authors(author_list: list[dict]) -> list[str]:
    """Convert author dicts to 'Given Family' format."""
    authors = []
    for author in author_list:
        given = author.get("given", "")
        family = author.get("family", "")
        if family:
            full_name = f"{given} {family}".strip() if given else family
            authors.append(full_name)
    return authors


def _parse_date(date_part: dict | None) -> str:
    """Parse date from date-parts format to ISO date string."""
    if not date_part:
        return ""
    parts = date_part.get("date-parts", [[]])
    if not parts or not parts[0]:
        return ""
    date_parts = parts[0]
    year = date_parts[0] if len(date_parts) > 0 else ""
    month = date_parts[1] if len(date_parts) > 1 else "01"
    day = date_parts[2] if len(date_parts) > 2 else "01"
    return f"{year}-{month:02}-{day:02}"


def _parse_datetime(dt_str: str | None) -> str:
    """Parse ISO datetime string to date string."""
    if not dt_str:
        return ""
    # Extract date portion from "2026-05-20T10:00:00Z"
    match = re.match(r'(\d{4}-\d{2}-\d{2})', dt_str)
    if match:
        return match.group(1)
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    records = []
    items = payload.get("message", {}).get("items", [])

    for item in items:
        # Extract required fields
        doi = item.get("DOI", "")
        if not doi:
            continue

        # Title: first element of title list
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        if not title:
            continue

        # Abstract: strip HTML tags
        abstract = item.get("abstract", "")
        summary = _strip_html_tags(abstract)

        # Authors
        author_list = item.get("author", [])
        authors = _format_authors(author_list)

        # Categories/subjects
        subjects = item.get("subject", [])
        categories = list(subjects) if subjects else []
        primary_category = categories[0] if categories else ""

        # Dates
        published_date = _parse_date(item.get("published"))
        updated_date = _parse_datetime(item.get("created", {}).get("date-time"))

        # URLs
        abs_url = item.get("URL", "")
        # For Crossref, pdf_url is typically same as abstract URL
        pdf_url = abs_url if abs_url else f"https://doi.org/{doi}"

        # Comment
        comment = f"Crossref record {doi}"

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published_date,
            updated=updated_date,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    # Ensure output directory exists
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)

    payload = None

    # Check if we should refresh from API or use existing snapshot
    if settings.refresh_source and settings.paths.raw_api_response.exists():
        # Crossref API endpoint
        base_url = "https://api.crossref.org/works"

        # Build query parameters
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }

        # Build full URL
        url = f"{base_url}?{urlencode(params)}"
        headers = {
            "User-Agent": "Latentia-DataPipeline/1.0 (mailto:lab@example.com)"
        }

        use_fallback = False

        # Try fetching from API with retry logic
        for attempt in range(3):
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=30) as response:
                    if response.status == 200:
                        payload = json.loads(response.read().decode("utf-8"))
                        break
                    elif response.status in (429, 503):
                        # Rate limit or service unavailable - use fallback
                        print(f"API returned {response.status}, using fallback snapshot.")
                        use_fallback = True
                        break
                    else:
                        raise RuntimeError(f"API returned status {response.status}")
            except Exception as e:
                if attempt < 2:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"API call failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"API call failed after 3 attempts: {e}. Using fallback snapshot.")
                    use_fallback = True

        # Fallback: read from existing snapshot if API failed
        if use_fallback or payload is None:
            if settings.paths.raw_api_response.exists():
                print(f"Loading from fallback snapshot: {settings.paths.raw_api_response}")
                with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            else:
                raise RuntimeError(
                    f"Cannot fetch from API and no fallback snapshot exists at {settings.paths.raw_api_response}"
                )
    else:
        # Use existing snapshot (no refresh needed)
        if settings.paths.raw_api_response.exists():
            print(f"Loading from existing snapshot: {settings.paths.raw_api_response}")
            with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            raise RuntimeError(
                f"No existing snapshot at {settings.paths.raw_api_response} and refresh_source is False"
            )

    # Save raw API response (preserving original)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Parse payload into PaperRecord list
    records = parse_crossref_payload(payload)

    # Save records to JSON
    records_data = [asdict(r) for r in records]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_data, f, indent=2, ensure_ascii=False)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        records_data = json.load(f)

    records = []
    for data in records_data:
        records.append(PaperRecord(**data))

    return records
