"""Seed the last N hours with realistic readings + aggregates.

Useful before a demo so the dashboard's 24h charts have history instead of
starting empty. Inserts raw readings (reusing the simulator's generator so
the daily cycle looks right), then runs the real transformation job for
each seeded hour -- exercising the actual pipeline path, not a shortcut.

    python -m scripts.seed_demo_data            # last 24 hours
    python -m scripts.seed_demo_data --hours 48
"""

import argparse
import logging
import time
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal, init_db
from app.models.reading_orm import RawReadingORM
from app.schemas.reading import SENSOR_SPECS
from jobs.transform import build_archive_sink, run
from simulator.simulate import SENSORS, generate_value

log = logging.getLogger("seed")

READINGS_PER_SENSOR_PER_HOUR = 6  # one every 10 minutes


def seed(hours: int) -> None:
    init_db()
    db = SessionLocal()
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    archive = build_archive_sink()
    try:
        for offset in range(hours, 0, -1):
            hour_start = now - timedelta(hours=offset)
            for spec in SENSORS:
                unit = SENSOR_SPECS[spec["sensor_type"]]["unit"]
                for i in range(READINGS_PER_SENSOR_PER_HOUR):
                    recorded_at = hour_start + timedelta(minutes=10 * i)
                    t = time.localtime(recorded_at.timestamp())
                    db.add(RawReadingORM(
                        sensor_id=spec["sensor_id"],
                        sensor_type=spec["sensor_type"],
                        value=generate_value(spec, t),
                        unit=unit,
                        recorded_at=recorded_at,
                        ingested_at=recorded_at,
                    ))
            db.commit()
            run(db, hour_start, archive)
        log.info("seeded %d hours x %d sensors x %d readings",
                 hours, len(SENSORS), READINGS_PER_SENSOR_PER_HOUR)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo readings + aggregates")
    parser.add_argument("--hours", type=int, default=24)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    seed(args.hours)
