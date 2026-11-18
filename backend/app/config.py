import os
import shutil
from pathlib import Path

# Project directories
BACKEND = Path(_file_).resolve().parents[1]

DATA = BACKEND / "data"

if os.environ.get("VERCEL"):
    # Vercel's project folder is read-only, so write working files to /tmp
    WORK = Path("/tmp")
    RAW = WORK / "raw"
    PROCESSED = WORK / "processed"
    REPORTS = WORK / "reports"
else:
    RAW = DATA / "raw"
    PROCESSED = DATA / "processed"
    REPORTS = BACKEND / "reports"

# Create directories automatically
for folder in [RAW, PROCESSED, REPORTS]:
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

# Database configuration
DB_SOURCE = DATA / "air_quality.db"

if os.environ.get("VERCEL"):
    # Work from a copy of the database in /tmp
    DB = Path("/tmp/air_quality.db")
    if DB_SOURCE.exists() and not DB.exists():
        shutil.copyfile(DB_SOURCE, DB)
else:
    DB = DB_SOURCE

DATABASE_URL = f"sqlite:///{DB.as_posix()}"

# Data collection settings
PAST_DAYS = 7

# Five Pakistani cities: latitude, longitude
CITIES = {
    "Lahore": (31.5204, 74.3587),
    "Islamabad": (33.6844, 73.0479),
    "Rawalpindi": (33.5651, 73.0169),
    "Sialkot": (32.4945, 74.5229),
    "Karachi": (24.8607, 67.0011),
}

# Air pollutants
POLLUTANTS = [
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
]

# Open-Meteo API
API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
# Current air-quality data API
CURRENT_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"