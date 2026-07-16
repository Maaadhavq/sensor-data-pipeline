"""Pydantic schemas for the analytics/insights endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HourlyAggregateOut(BaseModel):
    """One hour of aggregated readings for one sensor (chart-ready)."""

    sensor_id: str
    sensor_type: str
    hour_start: datetime
    avg_value: float
    min_value: float
    max_value: float
    reading_count: int

    model_config = {"from_attributes": True}


class SensorSummaryOut(BaseModel):
    """Current-state summary for one sensor: latest value + 24h stats.

    The 24h fields are None until the transformation job has produced
    aggregates for that sensor.
    """

    sensor_id: str
    sensor_type: str
    unit: str
    latest_value: float
    latest_at: datetime
    avg_24h: Optional[float] = None
    min_24h: Optional[float] = None
    max_24h: Optional[float] = None
    reading_count_24h: int = 0
