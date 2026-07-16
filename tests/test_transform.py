"""Transformation job tests on in-memory SQLite + a temp-dir archive sink."""

from datetime import datetime, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.reading_orm import HourlyAggregateORM, RawReadingORM
from jobs.sinks import LocalArchiveSink
from jobs.transform import last_completed_hour, run

HOUR = datetime(2026, 7, 16, 14, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def seed(db, sensor_id, sensor_type, value, minute, unit="celsius"):
    db.add(RawReadingORM(
        sensor_id=sensor_id, sensor_type=sensor_type, value=value, unit=unit,
        recorded_at=HOUR.replace(minute=minute),
        ingested_at=HOUR.replace(minute=minute),
    ))
    db.commit()


def seed_hour(db):
    seed(db, "temp-001", "temperature", 20.0, minute=5)
    seed(db, "temp-001", "temperature", 30.0, minute=35)
    seed(db, "hum-001", "humidity", 55.0, minute=10, unit="percent")
    # Outside the window: next hour -- must be excluded.
    db.add(RawReadingORM(
        sensor_id="temp-001", sensor_type="temperature", value=99.0,
        unit="celsius",
        recorded_at=HOUR.replace(hour=15, minute=1),
        ingested_at=HOUR.replace(hour=15, minute=1),
    ))
    db.commit()


def test_aggregates_computed_per_sensor(db, tmp_path):
    seed_hour(db)
    stats = run(db, HOUR, LocalArchiveSink(tmp_path))

    assert stats == {"readings": 3, "aggregates": 2, "archive": stats["archive"]}
    aggs = {a.sensor_id: a for a in db.query(HourlyAggregateORM).all()}
    assert len(aggs) == 2
    temp = aggs["temp-001"]
    assert temp.avg_value == 25.0
    assert temp.min_value == 20.0
    assert temp.max_value == 30.0          # 99.0 from the next hour excluded
    assert temp.reading_count == 2
    assert aggs["hum-001"].reading_count == 1


def test_rerun_is_idempotent(db, tmp_path):
    seed_hour(db)
    run(db, HOUR, LocalArchiveSink(tmp_path))
    # A late-arriving reading lands in the same hour, job re-runs.
    seed(db, "temp-001", "temperature", 40.0, minute=55)
    run(db, HOUR, LocalArchiveSink(tmp_path))

    rows = db.query(HourlyAggregateORM).filter_by(sensor_id="temp-001").all()
    assert len(rows) == 1                  # upserted, not duplicated
    assert rows[0].reading_count == 3
    assert rows[0].max_value == 40.0


def test_archive_parquet_written(db, tmp_path):
    seed_hour(db)
    stats = run(db, HOUR, LocalArchiveSink(tmp_path))

    expected = tmp_path / "raw/year=2026/month=07/day=16/hour=14/readings.parquet"
    assert expected.exists()
    assert stats["archive"] == str(expected)
    df = pd.read_parquet(expected)
    assert len(df) == 3
    assert set(df["sensor_id"]) == {"temp-001", "hum-001"}


def test_empty_hour_is_a_noop(db, tmp_path):
    stats = run(db, HOUR, LocalArchiveSink(tmp_path))
    assert stats == {"readings": 0, "aggregates": 0}
    assert db.query(HourlyAggregateORM).count() == 0


def test_last_completed_hour():
    now = datetime(2026, 7, 16, 15, 42, 10, tzinfo=timezone.utc)
    assert last_completed_hour(now) == datetime(2026, 7, 16, 14, 0, tzinfo=timezone.utc)
