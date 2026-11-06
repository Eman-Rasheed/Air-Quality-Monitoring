
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator
)


class AirQualityInput(BaseModel):

    city: str = Field(
        min_length=1,
        max_length=40
    )

    timestamp: datetime

    latitude: float = Field(
        ge=-90,
        le=90
    )

    longitude: float = Field(
        ge=-180,
        le=180
    )

    pm10: Optional[float] = None
    pm2_5: Optional[float] = None
    carbon_monoxide: Optional[float] = None
    nitrogen_dioxide: Optional[float] = None
    sulphur_dioxide: Optional[float] = None
    ozone: Optional[float] = None

    @field_validator("city")
    @classmethod
    def normalize_city(cls, value):
        return value.strip().title()


class AirQualityOutput(AirQualityInput):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
