
import logging
from datetime import datetime

import pandas as pd
import requests
from pydantic import ValidationError

from .config import CITIES, POLLUTANTS, CURRENT_API_URL
from .database import SessionLocal, Base, engine
from .models import AirQualityRecord
from .schemas import AirQualityInput


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# --------------------------------------------------
# 1. EXTRACT: Fetch current air-quality data
# --------------------------------------------------

def fetch_current_city(city, coordinates):
    latitude, longitude = coordinates

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(POLLUTANTS),
        "timezone": "Asia/Karachi",
    }

    response = requests.get(
        CURRENT_API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()
    current = data.get("current")

    if not current or "time" not in current:
        raise ValueError(f"No current data returned for {city}")

    row = {
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": current["time"],
    }

    for pollutant in POLLUTANTS:
        row[pollutant] = current.get(pollutant)

    logging.info("Fetched current data for %s", city)

    return row


# --------------------------------------------------
# 2. TRANSFORM: Clean data using Pandas
# --------------------------------------------------

def transform_current_data(rows):

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["city"] = (
        df["city"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    numeric_columns = [
        "latitude",
        "longitude",
        *POLLUTANTS
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    for pollutant in POLLUTANTS:
        df.loc[df[pollutant] < 0, pollutant] = float("nan")

    df.dropna(
        subset=[
            "city",
            "timestamp",
            "latitude",
            "longitude"
        ],
        inplace=True
    )

    df.drop_duplicates(
        subset=["city", "timestamp"],
        keep="last",
        inplace=True
    )

    return df.reset_index(drop=True)


# --------------------------------------------------
# 3. VALIDATE: Validate with Pydantic
# --------------------------------------------------

def validate_current_rows(df):

    valid = []
    rejected = 0

    for row in df.to_dict(orient="records"):

        row = {
            key: (
                None if pd.isna(value)
                else value
            )
            for key, value in row.items()
        }

        # Convert timestamp to a timezone-naive Python datetime
        row["timestamp"] = (
            pd.Timestamp(row["timestamp"])
            .to_pydatetime()
            .replace(tzinfo=None)
        )

        try:
            validated = AirQualityInput.model_validate(row)
            valid.append(validated.model_dump())

        except (ValidationError, ValueError, TypeError) as error:
            rejected += 1
            logging.warning("Record rejected: %s", error)

    logging.info(
        "Validation completed: %d valid, %d rejected",
        len(valid),
        rejected
    )

    return valid, rejected


# --------------------------------------------------
# 4. LOAD: Save records into SQLite
# --------------------------------------------------

# --------------------------------------------------
# 4. LOAD: Save records into SQLite
# --------------------------------------------------

def load_current_data(valid):

    if not valid:
        return 0

    saved = 0

    with SessionLocal() as db:

        try:
            for row in valid:

                existing = db.query(AirQualityRecord).filter_by(
                    city=row["city"],
                    timestamp=row["timestamp"]
                ).first()

                if existing:
                    for key, value in row.items():
                        setattr(existing, key, value)

                else:
                    db.add(AirQualityRecord(**row))

                saved += 1

            # --- 1-DAY ROLLING CLEANUP (Keeps exact 7 days, drops oldest day) ---
            from datetime import timedelta
            from sqlalchemy import func
            
            latest_record_date = db.query(func.max(AirQualityRecord.timestamp)).scalar()
            
            if latest_record_date:
                cutoff_date = latest_record_date - timedelta(days=7)
                
                delete_stmt = AirQualityRecord.__table__.delete().where(
                    AirQualityRecord.timestamp < cutoff_date
                )
                db.execute(delete_stmt)
            # ------------------------------------------------------------------

            db.commit()

        except Exception:
            db.rollback()
            logging.exception("Database loading failed")
            raise

    logging.info("Database loading completed: %d records", saved)

    return saved

# --------------------------------------------------
# 5. RUN COMPLETE CURRENT-DATA ETL
# --------------------------------------------------

def run_current_etl():

    Base.metadata.create_all(bind=engine)

    rows = []
    errors = []

    # Extract data for all five cities
    for city, coordinates in CITIES.items():

        try:
            row = fetch_current_city(city, coordinates)
            rows.append(row)

        except requests.RequestException as error:
            errors.append(f"{city}: API request failed: {error}")
            logging.exception("API request failed for %s", city)

        except (ValueError, KeyError) as error:
            errors.append(f"{city}: {error}")
            logging.exception("Data extraction failed for %s", city)

    if not rows:
        return {
            "status": "failed",
            "fetched_rows": 0,
            "valid_rows": 0,
            "rejected_rows": 0,
            "records_saved": 0,
            "errors": errors,
        }

    # Transform
    df = transform_current_data(rows)

    # Validate
    valid, rejected = validate_current_rows(df)

    # Load
    saved = load_current_data(valid)

    result = {
        "status": (
            "success" if not errors and rejected == 0
            else "partial_success" if saved > 0
            else "failed"
        ),
        "fetched_rows": len(rows),
        "valid_rows": len(valid),
        "rejected_rows": rejected,
        "records_saved": saved,
        "errors": errors,
        "completed_at": datetime.now().isoformat(),
    }

    logging.info("Current ETL completed: %s", result)

    return result


if __name__ == "__main__":
    print(run_current_etl())
