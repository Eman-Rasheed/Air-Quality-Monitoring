
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pandas as pd

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query
)

from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import CITIES, POLLUTANTS
from .database import Base, engine, SessionLocal
from .models import AirQualityRecord
from .schemas import AirQualityOutput
from .etl import run_etl
from .current_etl import run_current_etl


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

Base.metadata.create_all(engine)

historical_lock = threading.Lock()
current_lock = threading.Lock()

etl_status = {
    "status": "not_run",
    "message": "Historical ETL has not run yet."
}

current_etl_status = {
    "status": "not_run",
    "message": "Current-data ETL has not run yet."
}


# --------------------------------------------------
# HISTORICAL ETL WORKER
# --------------------------------------------------

def worker(locked=False):

    global etl_status

    if not locked and not historical_lock.acquire(blocking=False):
        return

    try:
        etl_status = {
            "status": "running",
            "message": "Historical ETL pipeline is running."
        }

        etl_status = run_etl()

    except Exception as exc:
        etl_status = {
            "status": "error",
            "message": str(exc)
        }

    finally:
        historical_lock.release()


# --------------------------------------------------
# CURRENT DATA ETL WORKER
# --------------------------------------------------

def current_worker(locked=False):

    global current_etl_status

    if not locked and not current_lock.acquire(blocking=False):
        return

    try:
        current_etl_status = {
            "status": "running",
            "message": "Current-data ETL is running."
        }

        current_etl_status = run_current_etl()

    except Exception as exc:
        current_etl_status = {
            "status": "error",
            "message": str(exc)
        }

    finally:
        current_lock.release()


# --------------------------------------------------
# APPLICATION LIFESPAN
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    with SessionLocal() as db:
        count = (
            db.query(func.count(AirQualityRecord.id))
            .scalar() or 0
        )

    if count == 0:
        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    yield


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Pakistan Air Quality ETL + EDA API",
    description=(
        "Historical and automatically updated air-quality "
        "monitoring API for five Pakistani cities."
    ),
    version="2.0.0",
    lifespan=lifespan
)


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

origins = [
    x.strip()
    for x in os.getenv(
        "FRONTEND_ORIGINS", ""
    ).split(",")
    if x.strip()
]

origins += [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(origins)),
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# DATABASE SESSION
# --------------------------------------------------

def db_session():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# --------------------------------------------------
# ROOT AND HEALTH
# --------------------------------------------------

@app.get("/")
def root():

    return {
        "name": "Pakistan Air Quality API",
        "version": "2.0.0",
        "documentation": "/docs",
        "available_endpoints": [
            "/api/cities",
            "/api/records",
            "/api/air-quality",
            "/api/summary",
            "/api/current",
            "/api/current/{city}",
            "/api/etl/status",
            "/api/current-etl/status"
        ]
    }


@app.get("/health")
def health():

    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat()
    }


# --------------------------------------------------
# CITY ENDPOINT
# --------------------------------------------------

@app.get("/api/cities")
def cities():

    return [
        {
            "name": city,
            "latitude": coords[0],
            "longitude": coords[1]
        }
        for city, coords in CITIES.items()
    ]


# --------------------------------------------------
# HISTORICAL ETL STATUS
# --------------------------------------------------

@app.get("/api/etl/status")
def get_etl_status():

    return etl_status


@app.post("/api/etl/run")
def refresh():

    if not historical_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Historical ETL is already running."
        )

    threading.Thread(
        target=worker,
        kwargs={"locked": True},
        daemon=True
    ).start()

    return {
        "status": "started",
        "message": "Historical ETL started."
    }


# --------------------------------------------------
# CURRENT ETL STATUS AND MANUAL REFRESH
# --------------------------------------------------

@app.get("/api/current-etl/status")
def get_current_etl_status():

    return current_etl_status


@app.post("/api/current-etl/run")
def refresh_current():

    if not current_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Current-data ETL is already running."
        )

    threading.Thread(
        target=current_worker,
        kwargs={"locked": True},
        daemon=True
    ).start()

    return {
        "status": "started",
        "message": "Current-data ETL started."
    }


# --------------------------------------------------
# COMMON RECORD QUERY
# --------------------------------------------------

def get_records(db, city=None, limit=500):

    query = db.query(AirQualityRecord)

    if city:

        if city.title() not in CITIES:
            raise HTTPException(
                status_code=404,
                detail=f"City '{city}' not found."
            )

        query = query.filter(
            func.lower(AirQualityRecord.city) == city.lower()
        )

    return (
        query
        .order_by(AirQualityRecord.timestamp.desc())
        .limit(limit)
        .all()
    )


# --------------------------------------------------
# ALL RECORDS
# --------------------------------------------------

@app.get(
    "/api/records",
    response_model=list[AirQualityOutput]
)
def records(
    city: str | None = None,
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(db_session)
):

    return get_records(db, city, limit)


# --------------------------------------------------
# HISTORICAL AIR QUALITY
# --------------------------------------------------

@app.get(
    "/api/air-quality",
    response_model=list[AirQualityOutput]
)
def air_quality(
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(db_session)
):

    return get_records(db, limit=limit)


@app.get(
    "/api/air-quality/{city}",
    response_model=list[AirQualityOutput]
)
def city_air_quality(
    city: str,
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(db_session)
):

    return get_records(db, city, limit)


# --------------------------------------------------
# CURRENT READINGS FOR ALL FIVE CITIES
# --------------------------------------------------

@app.get("/api/current")
def current_readings(
    db: Session = Depends(db_session)
):

    results = []

    for city in CITIES:

        record = (
            db.query(AirQualityRecord)
            .filter(
                func.lower(AirQualityRecord.city) == city.lower()
            )
            .order_by(AirQualityRecord.timestamp.desc())
            .first()
        )

        if record is None:
            continue

        results.append({
            "city": record.city,
            "timestamp": record.timestamp.isoformat(),
            "latitude": record.latitude,
            "longitude": record.longitude,
            "pollutants": {
                pollutant: getattr(record, pollutant)
                for pollutant in POLLUTANTS
            }
        })

    return {
        "count": len(results),
        "cities": results
    }


# --------------------------------------------------
# CURRENT READING FOR ONE CITY
# --------------------------------------------------

@app.get("/api/current/{city}")
def current_city_reading(
    city: str,
    db: Session = Depends(db_session)
):

    if city.title() not in CITIES:
        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' not found."
        )

    record = (
        db.query(AirQualityRecord)
        .filter(
            func.lower(AirQualityRecord.city) == city.lower()
        )
        .order_by(AirQualityRecord.timestamp.desc())
        .first()
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No readings found for {city}."
        )

    return {
        "city": record.city,
        "timestamp": record.timestamp.isoformat(),
        "latitude": record.latitude,
        "longitude": record.longitude,
        "pollutants": {
            pollutant: getattr(record, pollutant)
            for pollutant in POLLUTANTS
        }
    }


# --------------------------------------------------
# SUMMARY AND EDA
# --------------------------------------------------

@app.get("/api/summary")
def summary(db: Session = Depends(db_session)):

    rows = (
        db.query(AirQualityRecord)
        .order_by(AirQualityRecord.timestamp)
        .all()
    )

    if not rows:
        return {
            "record_count": 0,
            "cities": list(CITIES),
            "city_summaries": [],
            "hourly": [],
            "correlations": {}
        }

    df = pd.DataFrame([
        {
            "city": row.city,
            "timestamp": row.timestamp,
            **{
                pollutant: getattr(row, pollutant)
                for pollutant in POLLUTANTS
            }
        }
        for row in rows
    ])

    city_summaries = []

    for city in CITIES:

        sub = df[df["city"] == city]
        stats = {}

        for pollutant in POLLUTANTS:

            values = pd.to_numeric(
                sub[pollutant],
                errors="coerce"
            ).dropna()

            stats[pollutant] = {
                "mean": (
                    round(float(values.mean()), 2)
                    if len(values) else None
                ),
                "max": (
                    round(float(values.max()), 2)
                    if len(values) else None
                )
            }

        city_summaries.append({
            "city": city,
            "record_count": len(sub),
            "pollutants": stats
        })

    df["hour"] = pd.to_datetime(
        df["timestamp"]
    ).dt.hour

    hourly = []

    for hour, group in df.groupby("hour"):

        point = {"hour": int(hour)}

        for pollutant in POLLUTANTS:

            values = pd.to_numeric(
                group[pollutant],
                errors="coerce"
            ).dropna()

            point[pollutant] = (
                round(float(values.mean()), 2)
                if len(values) else None
            )

        hourly.append(point)

    correlation = (
        df[POLLUTANTS]
        .corr(numeric_only=True)
        .round(3)
        .fillna(0)
        .to_dict()
    )

    return {
        "record_count": len(df),
        "cities": list(CITIES),
        "city_summaries": city_summaries,
        "hourly": hourly,
        "correlations": correlation
    }
