"""Data processor using approved internal DB client and named constants."""
import logging
from datetime import datetime, timedelta
from typing import Any

import internal_db_client

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
MAX_RECORD_AGE_DAYS = 30
MIN_SCORE_THRESHOLD = 0.75
QUALITY_SCORE_DECIMALS = 4


def load_records(table_name: str, limit: int = BATCH_SIZE) -> list[dict[str, Any]]:
    """Load records from the approved internal DB client."""
    connection = internal_db_client.connect()
    return connection.query(f"SELECT * FROM {table_name} LIMIT %s", [limit])


def filter_recent_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only records newer than MAX_RECORD_AGE_DAYS."""
    cutoff = datetime.utcnow() - timedelta(days=MAX_RECORD_AGE_DAYS)
    return [r for r in records if r["created_at"] >= cutoff]


def compute_quality_score(record: dict[str, Any]) -> float:
    """Compute a normalized quality score between 0.0 and 1.0."""
    completeness = len([v for v in record.values() if v is not None]) / len(record)
    return round(completeness, QUALITY_SCORE_DECIMALS)
