from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint
from .database import Base
class AirQualityRecord(Base):
    __tablename__ = "air_quality_records"
    __table_args__ = (UniqueConstraint("city", "timestamp", name="uq_city_timestamp"),)
    id = Column(Integer, primary_key=True)
    city = Column(String(40), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    pm10 = Column(Float)
    pm2_5 = Column(Float)
    carbon_monoxide = Column(Float)
    nitrogen_dioxide = Column(Float)
    sulphur_dioxide = Column(Float)
    ozone = Column(Float)
