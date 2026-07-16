"""API tests against an in-memory SQLite database.

The repository pattern makes this possible: tests override the `get_db`
dependency so no Postgres instance is needed in CI.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

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


@pytest.fixture()
def client():
    # Scoped to the fixture (not module import time) so parallel test
    # modules with their own engines don't clobber each other's override.
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ingest_valid_reading(client):
    resp = client.post(
        "/sensors/readings",
        json={"sensor_id": "temp-001", "sensor_type": "temperature", "value": 23.4},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sensor_id"] == "temp-001"
    assert body["unit"] == "celsius"
    assert body["recorded_at"] is not None  # server filled it in


def test_reject_unknown_sensor_type(client):
    resp = client.post(
        "/sensors/readings",
        json={"sensor_id": "x-1", "sensor_type": "co2", "value": 400},
    )
    assert resp.status_code == 422


def test_reject_out_of_range_value(client):
    resp = client.post(
        "/sensors/readings",
        json={"sensor_id": "hum-001", "sensor_type": "humidity", "value": 130},
    )
    assert resp.status_code == 422


def test_latest_returns_one_reading_per_sensor(client):
    readings = [
        ("temp-001", "temperature", 20.0, "2026-07-16T10:00:00Z"),
        ("temp-001", "temperature", 25.0, "2026-07-16T11:00:00Z"),  # newer
        ("hum-001", "humidity", 55.0, "2026-07-16T10:30:00Z"),
    ]
    for sensor_id, sensor_type, value, ts in readings:
        resp = client.post(
            "/sensors/readings",
            json={
                "sensor_id": sensor_id,
                "sensor_type": sensor_type,
                "value": value,
                "recorded_at": ts,
            },
        )
        assert resp.status_code == 201

    resp = client.get("/sensors/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    by_sensor = {r["sensor_id"]: r for r in body}
    assert by_sensor["temp-001"]["value"] == 25.0  # newer reading wins
    assert by_sensor["hum-001"]["value"] == 55.0
