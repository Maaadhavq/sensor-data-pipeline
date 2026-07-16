"""Data access for raw readings.

Only this layer touches SQLAlchemy queries -- the service above it works
with plain objects. Same repository pattern as employee-management-api.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.reading_orm import RawReadingORM


class ReadingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        sensor_id: str,
        sensor_type: str,
        value: float,
        unit: str,
        recorded_at: datetime,
    ) -> RawReadingORM:
        reading = RawReadingORM(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            value=value,
            unit=unit,
            recorded_at=recorded_at,
        )
        self.db.add(reading)
        self.db.commit()
        self.db.refresh(reading)
        return reading

    def latest_per_sensor(self) -> list[RawReadingORM]:
        """Most recent reading for every sensor.

        Uses a portable GROUP BY + MAX subquery (works on Postgres and the
        SQLite test database alike) instead of Postgres-only DISTINCT ON.
        """
        latest = (
            self.db.query(
                RawReadingORM.sensor_id,
                func.max(RawReadingORM.recorded_at).label("max_recorded_at"),
            )
            .group_by(RawReadingORM.sensor_id)
            .subquery()
        )
        return (
            self.db.query(RawReadingORM)
            .join(
                latest,
                (RawReadingORM.sensor_id == latest.c.sensor_id)
                & (RawReadingORM.recorded_at == latest.c.max_recorded_at),
            )
            .order_by(RawReadingORM.sensor_id)
            .all()
        )
