"""Data access for the analytics tables."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.reading_orm import HourlyAggregateORM


class InsightsRepository:
    def __init__(self, db: Session):
        self.db = db

    def hourly(self, hours: int, sensor_id: Optional[str] = None) -> list[HourlyAggregateORM]:
        """Hourly aggregate rows for the last `hours` hours, oldest first."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = (
            self.db.query(HourlyAggregateORM)
            .filter(HourlyAggregateORM.hour_start >= cutoff)
        )
        if sensor_id:
            query = query.filter(HourlyAggregateORM.sensor_id == sensor_id)
        return query.order_by(
            HourlyAggregateORM.hour_start, HourlyAggregateORM.sensor_id
        ).all()

    def stats_24h(self) -> dict[str, dict]:
        """Per-sensor stats over the last 24h of aggregates.

        Average is weighted by reading_count so hours with more readings
        count proportionally, not equally.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        rows = (
            self.db.query(
                HourlyAggregateORM.sensor_id,
                (
                    func.sum(HourlyAggregateORM.avg_value * HourlyAggregateORM.reading_count)
                    / func.sum(HourlyAggregateORM.reading_count)
                ).label("avg_24h"),
                func.min(HourlyAggregateORM.min_value).label("min_24h"),
                func.max(HourlyAggregateORM.max_value).label("max_24h"),
                func.sum(HourlyAggregateORM.reading_count).label("reading_count_24h"),
            )
            .filter(HourlyAggregateORM.hour_start >= cutoff)
            .group_by(HourlyAggregateORM.sensor_id)
            .all()
        )
        return {
            r.sensor_id: {
                "avg_24h": round(float(r.avg_24h), 3),
                "min_24h": r.min_24h,
                "max_24h": r.max_24h,
                "reading_count_24h": int(r.reading_count_24h),
            }
            for r in rows
        }
