"""Business logic for sensor readings.

Fills in server-side fields (canonical unit, missing timestamps) before
handing off to the repository.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.reading_orm import RawReadingORM
from app.repository.reading_repo import ReadingRepository
from app.schemas.reading import SENSOR_SPECS, ReadingCreate


class ReadingService:
    def __init__(self, db: Session):
        self.repo = ReadingRepository(db)

    def ingest(self, payload: ReadingCreate) -> RawReadingORM:
        recorded_at = payload.recorded_at or datetime.now(timezone.utc)
        unit = SENSOR_SPECS[payload.sensor_type]["unit"]
        return self.repo.create(
            sensor_id=payload.sensor_id,
            sensor_type=payload.sensor_type,
            value=payload.value,
            unit=unit,
            recorded_at=recorded_at,
        )

    def latest_readings(self) -> list[RawReadingORM]:
        return self.repo.latest_per_sensor()
