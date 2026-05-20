"""Service layer with separated responsibilities, env-based secrets, and cloud storage."""
import csv
import io
import logging
import os

import boto3

logger = logging.getLogger(__name__)

_S3_BUCKET = os.environ["STORAGE_BUCKET"]
_DB_PASSWORD = os.environ["DB_PASSWORD"]


class ReportService:
    """Generates and uploads reports to cloud storage."""

    def __init__(self, s3_client=None) -> None:
        self._s3 = s3_client or boto3.client("s3")

    def generate_report(self, data: list[dict]) -> bytes:
        """Transform raw data into a CSV-formatted byte payload."""
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return buffer.getvalue().encode("utf-8")

    def upload_report(self, payload: bytes, report_name: str) -> str:
        """Upload report bytes to S3 and return the object key."""
        key = f"reports/{report_name}"
        self._s3.put_object(Bucket=_S3_BUCKET, Key=key, Body=payload)
        logger.info("Report uploaded to s3://%s/%s", _S3_BUCKET, key)
        return key
