"""Sensor endpoints: ingestion + real-time latest values."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.reading import ReadingCreate, ReadingOut
from app.services.reading_service import ReadingService

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.post(
    "/readings",
    response_model=ReadingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a sensor reading",
)
def ingest_reading(payload: ReadingCreate, db: Session = Depends(get_db)) -> ReadingOut:
    """Accept one reading from a sensor (or the simulator) and store it
    in the raw zone (`raw_readings`)."""
    return ReadingService(db).ingest(payload)


@router.get(
    "/latest",
    response_model=list[ReadingOut],
    summary="Latest reading per sensor",
)
def latest_readings(db: Session = Depends(get_db)) -> list[ReadingOut]:
    """Real-time view: the most recent stored reading for every sensor."""
    return ReadingService(db).latest_readings()
