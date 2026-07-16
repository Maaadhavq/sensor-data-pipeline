"""Analytics endpoints -- what the dashboard charts are built from."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.insights import HourlyAggregateOut, SensorSummaryOut
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get(
    "/hourly",
    response_model=list[HourlyAggregateOut],
    summary="Hourly aggregates for charting",
)
def hourly_insights(
    hours: int = Query(default=24, ge=1, le=168,
                       description="Look-back window in hours (max 7 days)"),
    sensor_id: Optional[str] = Query(default=None,
                                     description="Filter to one sensor"),
    db: Session = Depends(get_db),
) -> list[HourlyAggregateOut]:
    """Avg/min/max per sensor per hour, oldest first -- feed it straight
    into a line chart."""
    return InsightsService(db).hourly(hours, sensor_id)


@router.get(
    "/summary",
    response_model=list[SensorSummaryOut],
    summary="Current-state summary per sensor",
)
def summary_insights(db: Session = Depends(get_db)) -> list[SensorSummaryOut]:
    """Latest value per sensor plus 24h stats (weighted avg, min, max,
    reading count) from the aggregates table."""
    return InsightsService(db).summary()
