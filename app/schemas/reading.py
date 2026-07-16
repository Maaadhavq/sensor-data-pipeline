"""Pydantic schemas for sensor readings.

Validation lives here (at the edge): unknown sensor types and physically
impossible values are rejected with a 422 before anything touches the DB.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SensorType = Literal["temperature", "humidity"]

# Physically plausible ranges + canonical unit per sensor type.
SENSOR_SPECS: dict[str, dict] = {
    "temperature": {"min": -40.0, "max": 85.0, "unit": "celsius"},
    "humidity": {"min": 0.0, "max": 100.0, "unit": "percent"},
}


class ReadingCreate(BaseModel):
    """Payload the simulator POSTs to /sensors/readings."""

    sensor_id: str = Field(min_length=1, max_length=64, examples=["temp-001"])
    sensor_type: SensorType
    value: float = Field(examples=[23.4])
    # Optional: if the device doesn't send a timestamp, the server fills it in.
    recorded_at: Optional[datetime] = None

    @model_validator(mode="after")
    def value_in_physical_range(self) -> "ReadingCreate":
        spec = SENSOR_SPECS[self.sensor_type]
        if not (spec["min"] <= self.value <= spec["max"]):
            raise ValueError(
                f"{self.sensor_type} value {self.value} outside plausible "
                f"range [{spec['min']}, {spec['max']}]"
            )
        return self


class ReadingOut(BaseModel):
    """A stored reading, as returned by the API."""

    id: int
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    recorded_at: datetime
    ingested_at: datetime

    model_config = {"from_attributes": True}
