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
            "message":
