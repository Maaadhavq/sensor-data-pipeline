"""Archive sinks -- where the raw hourly batch lands as Parquet.

Same adapter idea as sales-etl-pipeline's `DataSink`: `ArchiveSink` is the
interface, `LocalArchiveSink` writes to disk for dev, `S3ArchiveSink` writes
to the S3 data lake in prod. The transformation job doesn't care which one
it gets -- only the adapter moves.

Partition layout (Hive-style, so Athena/Glue could query it later):
    raw/year=2026/month=07/day=16/hour=15/readings.parquet
"""

import io
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger("transform")


def partition_key(hour_start: datetime) -> str:
    return (
        f"raw/year={hour_start:%Y}/month={hour_start:%m}/"
        f"day={hour_start:%d}/hour={hour_start:%H}/readings.parquet"
    )


class ArchiveSink(ABC):
    @abstractmethod
    def write(self, df: pd.DataFrame, hour_start: datetime) -> str:
        """Persist the raw batch; returns the destination for logging."""


class LocalArchiveSink(ArchiveSink):
    """Dev sink: mirrors the S3 layout under a local directory."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def write(self, df: pd.DataFrame, hour_start: datetime) -> str:
        path = self.root / partition_key(hour_start)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        log.info("archived %d rows -> %s", len(df), path)
        return str(path)


class S3ArchiveSink(ArchiveSink):
    """Prod sink: Parquet into the S3 data lake bucket.

    boto3 picks up credentials from the EC2 instance's IAM role -- no keys
    in config, same as the employee API's S3 export feature.
    """

    def __init__(self, bucket: str, region: str):
        import boto3  # imported here so dev/tests don't need AWS at all

        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    def write(self, df: pd.DataFrame, hour_start: datetime) -> str:
        key = partition_key(hour_start)
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=buf.getvalue())
        dest = f"s3://{self.bucket}/{key}"
        log.info("archived %d rows -> %s", len(df), dest)
        return dest
