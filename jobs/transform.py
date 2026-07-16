"""Hourly transformation job.

For one hour window:
  1. read that hour's raw readings from `raw_readings`
  2. compute avg/min/max/count per sensor -> upsert into `hourly_aggregates`
  3. archive the raw batch as Parquet via an ArchiveSink (local dir or S3)

Idempotent: re-running an hour upserts the same aggregate rows and simply
overwrites the same Parquet partition, so a cron retry can never duplicate.

Run from cron on EC2 (inside the API container, which has the DB URL):
    5 * * * * cd ~/sensor-data-pipeline && docker compose -f docker-compose.prod.yml exec -T api python -m jobs.transform

Manual/backfill:
    python -m jobs.transform                      # last completed hour
    python -m jobs.transform --hour 2026-07-16T14 # a specific hour (UTC)
"""

import argparse
import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models.reading_orm import HourlyAggregateORM, RawReadingORM
from jobs.sinks import ArchiveSink, LocalArchiveSink, S3ArchiveSink

log = logging.getLogger("transform")


def last_completed_hour(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)


def fetch_raw_batch(db: Session, hour_start: datetime) -> pd.DataFrame:
    hour_end = hour_start + timedelta(hours=1)
    rows = (
        db.query(RawReadingORM)
        .filter(RawReadingORM.recorded_at >= hour_start,
                RawReadingORM.recorded_at < hour_end)
        .all()
    )
    return pd.DataFrame(
        [
            {
                "id": r.id,
                "sensor_id": r.sensor_id,
                "sensor_type": r.sensor_type,
                "value": r.value,
                "unit": r.unit,
                "recorded_at": r.recorded_at,
                "ingested_at": r.ingested_at,
            }
            for r in rows
        ]
    )


def compute_aggregates(df: pd.DataFrame, hour_start: datetime) -> list[dict]:
    grouped = (
        df.groupby(["sensor_id", "sensor_type"])["value"]
        .agg(avg_value="mean", min_value="min", max_value="max", reading_count="count")
        .reset_index()
    )
    records = grouped.to_dict("records")
    for rec in records:
        rec["hour_start"] = hour_start
        rec["avg_value"] = round(float(rec["avg_value"]), 3)
        rec["reading_count"] = int(rec["reading_count"])
    return records


def upsert_aggregates(db: Session, records: list[dict]) -> None:
    """Portable upsert keyed on (sensor_id, hour_start) -- works on both
    Postgres and the SQLite test database."""
    for rec in records:
        existing = (
            db.query(HourlyAggregateORM)
            .filter(HourlyAggregateORM.sensor_id == rec["sensor_id"],
                    HourlyAggregateORM.hour_start == rec["hour_start"])
            .one_or_none()
        )
        if existing:
            for field in ("sensor_type", "avg_value", "min_value",
                          "max_value", "reading_count"):
                setattr(existing, field, rec[field])
        else:
            db.add(HourlyAggregateORM(**rec))
    db.commit()


def run(db: Session, hour_start: datetime, archive: ArchiveSink) -> dict:
    """Core job, separated from main() so tests can drive it directly."""
    df = fetch_raw_batch(db, hour_start)
    if df.empty:
        log.info("no readings in hour starting %s -- nothing to do", hour_start)
        return {"readings": 0, "aggregates": 0}

    records = compute_aggregates(df, hour_start)
    upsert_aggregates(db, records)
    dest = archive.write(df, hour_start)
    log.info("hour %s: %d readings -> %d aggregate rows, archived to %s",
             hour_start, len(df), len(records), dest)
    return {"readings": len(df), "aggregates": len(records), "archive": dest}


def build_archive_sink() -> ArchiveSink:
    if settings.S3_BUCKET_NAME:
        return S3ArchiveSink(settings.S3_BUCKET_NAME, settings.AWS_REGION)
    from app.config import BASE_DIR
    return LocalArchiveSink(BASE_DIR / "data" / "lake")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hourly aggregation + archival job")
    parser.add_argument("--hour", help="Hour to process, UTC (e.g. 2026-07-16T14). "
                                       "Default: last completed hour.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if args.hour:
        hour_start = datetime.fromisoformat(args.hour).replace(
            minute=0, second=0, microsecond=0)
        if hour_start.tzinfo is None:
            hour_start = hour_start.replace(tzinfo=timezone.utc)
    else:
        hour_start = last_completed_hour()

    from app.database import SessionLocal, init_db
    init_db()  # ensure tables exist on first run
    db = SessionLocal()
    try:
        run(db, hour_start, build_archive_sink())
    finally:
        db.close()


if __name__ == "__main__":
    main()
