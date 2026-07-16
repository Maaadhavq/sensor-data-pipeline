"""Application configuration.

Centralises settings so they are not scattered as magic values across the
codebase. Same pattern as employee-management-api.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Project root: .../sensor-data-pipeline
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """Runtime settings, overridable via environment variables."""

    APP_NAME: str = "Sensor Data Pipeline API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "IoT sensor data pipeline: ingests temperature/humidity readings, "
        "serves real-time values, and exposes hourly analytics computed by "
        "a scheduled transformation job (RDS + S3 data lake)."
    )

    # New database on the same RDS instance -- does NOT touch employee_db.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:madhav@localhost:5432/sensor_db"
    )
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "False").lower() in ("true", "1", "yes")

    # Deployment environment: "development" locally, "production" on AWS.
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # AWS / S3 settings (used by the Phase 2 transformation job for the
    # Parquet data lake). On EC2 these credentials are supplied automatically
    # by the attached IAM role, so AWS keys are deliberately NOT read here.
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-south-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
