"""Data processor using approved internal DB client and named constants."""
import logging
from datetime import datetime, timedelta
from typing import Any

import internal_db_client

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
MAX_RECORD_AGE_DAYS = 30
MIN_SCORE_THRESHOLD = 0.75


def load_records(table_name: str, limit: int = BATCH_SIZE) -> list[dict[str, Any]]:
    """Load records from the approved internal DB client."""
    connection = internal_db_client.connect()
    return connection.query(f"SELECT * FROM {table_name} LIMIT %s", [limit])


def filter_quality_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter records by age and minimum quality score."""
    cutoff = datetime.utcnow() - timedelta(days=MAX_RECORD_AGE_DAYS)
    return [
        r for r in records
        if r["created_at"] >= cutoff and r["score"] >= MIN_SCORE_THRESHOLD
    ]
