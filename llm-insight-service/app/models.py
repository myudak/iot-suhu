from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, validator


def parse_iso8601(value: str) -> datetime:
    """Parse string into timezone-aware UTC datetime."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TelemetryMessage(BaseModel):
    device_id: str = Field(..., alias="device_id")
    ts: datetime = Field(..., alias="ts")
    temp_c: float = Field(..., alias="temp_c")
    humidity: float = Field(..., alias="humidity")
    rssi: Optional[int] = Field(None, alias="rssi")
    fw: Optional[str] = Field(None, alias="fw")

    @validator("device_id")
    def validate_device_id(cls, value):  # type: ignore[override]
        value = value.strip()
        if not value:
            raise ValueError("device_id is required")
        return value

    @validator("ts", pre=True)
    def validate_ts(cls, value):  # type: ignore[override]
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        if isinstance(value, str):
            try:
                return parse_iso8601(value)
            except ValueError as exc:
                raise ValueError(f"Invalid timestamp: {value}") from exc
        raise ValueError("Unsupported timestamp type")


class InsightMessage(BaseModel):
    device_id: str
    ts: datetime
    level: str
    summary: str
    reason: str
    last_temp_c: float
    window_avg_c: float
    recommendation: Optional[str] = None

    @validator("device_id")
    def validate_device_id(cls, value):  # type: ignore[override]
        value = value.strip()
        if not value:
            raise ValueError("device_id is required")
        return value

    class Config:
        json_encoders = {datetime: lambda v: v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")}
