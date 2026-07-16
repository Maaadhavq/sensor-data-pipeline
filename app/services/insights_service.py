"""Business logic for analytics insights.

The summary endpoint stitches two sources together: the latest raw reading
per sensor (real-time) and the last 24h of hourly aggregates (analytics).
A sensor that has readings but no aggregates yet (transform job hasn't run)
still appears -- with the 24h fields left as None.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.reading_orm import HourlyAggregateORM
from app.repository.insights_repo import InsightsRepository
from app.repository.reading_repo import ReadingRepository
from app.schemas.insights import SensorSummaryOut


class InsightsService:
    def __init__(self, db: Session):
        self.insights_repo = InsightsRepository(db)
        self.reading_repo = ReadingRepository(db)

    def hourly(self, hours: int, sensor_id: Optional[str] = None) -> list[HourlyAggregateORM]:
        return self.insights_repo.hourly(hours, sensor_id)

    def summary(self) -> list[SensorSummaryOut]:
        stats = self.insights_repo.stats_24h()
        summaries = []
        for reading in self.reading_repo.latest_per_sensor():
            sensor_stats = stats.get(reading.sensor_id, {})
            summaries.append(
                SensorSummaryOut(
                    sensor_id=reading.sensor_id,
                    sensor_type=reading.sensor_type,
                    unit=reading.unit,
                    latest_value=reading.value,
                    latest_at=reading.recorded_at,
                    **sensor_stats,
                )
            )
        return summaries
