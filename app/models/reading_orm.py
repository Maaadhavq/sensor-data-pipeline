"""ORM models for the two tables in the pipeline.

`raw_readings`  -- every reading the ingestion API accepts (the raw zone).
`hourly_aggregates` -- avg/min/max per sensor per hour, written by the
Phase 2 transformation job (the analytics zone, queryable for insights).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RawReadingORM(Base):
    __tablename__ = "raw_readings"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(64), nullable=False, index=True)
    sensor_type = Column(String(32), nullable=False)   # "temperature" | "humidity"
    value = Column(Float, nullable=False)
    unit = Column(String(16), nullable=False)          # "celsius" | "percent"
    # When the sensor says it took the reading (device clock).
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    # When the API actually received it (server clock) -- lets the
    # transformation job pick up late-arriving data reliably.
    ingested_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class HourlyAggregateORM(Base):
    __tablename__ = "hourly_aggregates"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(64), nullable=False, index=True)
    sensor_type = Column(String(32), nullable=False)
    hour_start = Column(DateTime(timezone=True), nullable=False, index=True)
    avg_value = Column(Float, nullable=False)
    min_value = Column(Float, nullable=False)
    max_value = Column(Float, nullable=False)
    reading_count = Column(Integer, nullable=False)

    # One row per sensor per hour -- makes the transformation job idempotent
    # (re-running an hour upserts instead of duplicating).
    __table_args__ = (
        UniqueConstraint("sensor_id", "hour_start", name="uq_sensor_hour"),
    )
