"""Insights endpoint tests: seed aggregates + raw readings, hit the API."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.reading_orm import HourlyAggregateORM, RawReadingORM

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


NOW = datetime.now(timezone.utc)


def hour_ago(n: int) -> datetime:
    return (NOW - timedelta(hours=n)).replace(minute=0, second=0, microsecond=0)


@pytest.fixture()
def client():
    # Scoped to the fixture (not module import time) so parallel test
    # modules with their own engines don't clobber each other's override.
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Aggregates: two recent hours + one far outside any 24h window.
    db.add_all([
        HourlyAggregateORM(sensor_id="temp-001", sensor_type="temperature",
                           hour_start=hour_ago(2), avg_value=22.0,
                           min_value=20.0, max_value=24.0, reading_count=10),
        HourlyAggregateORM(sensor_id="temp-001", sensor_type="temperature",
                           hour_start=hour_ago(1), avg_value=26.0,
                           min_value=25.0, max_value=27.0, reading_count=30),
        HourlyAggregateORM(sensor_id="temp-001", sensor_type="temperature",
                           hour_start=hour_ago(30), avg_value=99.0,
                           min_value=99.0, max_value=99.0, reading_count=5),
    ])
    # Latest raw readings: temp-001 has aggregates, hum-001 does not (yet).
    db.add_all([
        RawReadingORM(sensor_id="temp-001", sensor_type="temperature",
                      value=25.5, unit="celsius",
                      recorded_at=NOW, ingested_at=NOW),
        RawReadingORM(sensor_id="hum-001", sensor_type="humidity",
                      value=61.0, unit="percent",
                      recorded_at=NOW, ingested_at=NOW),
    ])
    db.commit()
    db.close()
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def test_hourly_respects_window_and_order(client):
    body = client.get("/insights/hourly?hours=24").json()
    assert [b["avg_value"] for b in body] == [22.0, 26.0]  # 30h-old row excluded
    assert body[0]["hour_start"] < body[1]["hour_start"]   # oldest first

    wide = client.get("/insights/hourly?hours=48").json()
    assert len(wide) == 3                                  # now includes it


def test_hourly_sensor_filter_and_validation(client):
    assert client.get("/insights/hourly?sensor_id=nope").json() == []
    assert client.get("/insights/hourly?hours=0").status_code == 422
    assert client.get("/insights/hourly?hours=999").status_code == 422


def test_summary_merges_latest_and_24h_stats(client):
    body = client.get("/insights/summary").json()
    by_sensor = {s["sensor_id"]: s for s in body}
    assert len(body) == 2

    temp = by_sensor["temp-001"]
    assert temp["latest_value"] == 25.5
    # Weighted avg: (22*10 + 26*30) / 40 = 25.0 -- not the naive 24.0.
    assert temp["avg_24h"] == 25.0
    assert temp["min_24h"] == 20.0
    assert temp["max_24h"] == 27.0
    assert temp["reading_count_24h"] == 40

    hum = by_sensor["hum-001"]                # no aggregates yet
    assert hum["latest_value"] == 61.0
    assert hum["avg_24h"] is None
    assert hum["reading_count_24h"] == 0
