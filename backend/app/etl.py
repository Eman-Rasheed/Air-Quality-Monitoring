
import logging
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from pydantic import ValidationError
from sqlalchemy.dialects.sqlite import insert

from .config import (
    API_URL,
    CITIES,
    POLLUTANTS,
    PAST_DAYS,
    RAW,
    PROCESSED,
)

from .database import Base, SessionLocal, engine
from .models import AirQualityRecord
from .schemas import AirQualityInput


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# --------------------------------------------------
# 1. EXTRACT: Fetch hourly data from Open-Meteo API
# --------------------------------------------------

def fetch_city(city, coords):
    lat, lon = coords

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(POLLUTANTS),
        "timezone": "Asia/Karachi",
        "past_days": PAST_DAYS,
        "forecast_days": 0,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=45
    )

    response.raise_for_status()

    api_data = response.json()

    hourly = api_data.get("hourly", {})

    if not hourly or "time" not in hourly:
        raise ValueError(
            f"No hourly records returned for {city}"
        )

    df = pd.DataFrame(hourly)

    # Add city information
    df.insert(0, "city", city)

    df["latitude"] = lat
    df["longitude"] = lon

    # Convert API time into datetime
    df["timestamp"] = pd.to_datetime(
        df.pop("time"),
        errors="coerce"
    )

    logging.info(
        "%s: Extracted %d records",
        city,
        len(df)
    )

    return df


# --------------------------------------------------
# 2. TRANSFORM: Clean and prepare the data
# --------------------------------------------------

def clean_data(frame):

    df = frame.copy()

    if df.empty:
        return df

    # Standardize city names
    df["city"] = (
        df["city"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    # Convert timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Ensure all pollutant columns exist
    for col in POLLUTANTS:
        if col not in df.columns:
            df[col] = float("nan")

    # Convert numeric columns
    numeric_columns = [
        "latitude",
        "longitude",
        *POLLUTANTS
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # Remove rows without essential information
    df.dropna(
        subset=[
            "city",
            "timestamp",
            "latitude",
            "longitude"
        ],
        inplace=True
    )

    # Remove duplicate city timestamps
    df.drop_duplicates(
        subset=["city", "timestamp"],
        keep="last",
        inplace=True
    )

    # Negative pollutant values are treated as missing
    for col in POLLUTANTS:
        df.loc[df[col] < 0, col] = float("nan")

    # Arrange columns
    df = df[
        [
            "city",
            "timestamp",
            "latitude",
            "longitude",
            *POLLUTANTS
        ]
    ]

    # Sort records
    df = df.sort_values(
        ["city", "timestamp"]
    ).reset_index(drop=True)

    logging.info(
        "Cleaning completed: %d records",
        len(df)
    )

    return df


# --------------------------------------------------
# 3. VALIDATE: Validate records using Pydantic
# --------------------------------------------------

def validate_rows(df):

    valid = []
    rejected = 0

    for row in df.to_dict("records"):

        # Convert Pandas missing values into None
        row = {
            key: (
                None if pd.isna(value)
                else value
            )
            for key, value in row.items()
        }

        try:

            validated_record = (
                AirQualityInput
                .model_validate(row)
                .model_dump()
            )

            valid.append(validated_record)

        except (
            ValidationError,
            ValueError,
            TypeError
        ):

            rejected += 1

    logging.info(
        "Validation completed: %d valid, %d rejected",
        len(valid),
        rejected
    )

    return valid, rejected


# --------------------------------------------------
# 4. LOAD: Save validated records into SQLite
# --------------------------------------------------

# --------------------------------------------------
# 4. LOAD: Save validated records into SQLite
# --------------------------------------------------

def load_to_database(valid):

    if not valid:
        return 0

    with SessionLocal() as db:

        try:

            for row in valid:

                row = row.copy()

                # Convert timestamp to Python datetime
                row["timestamp"] = pd.Timestamp(
                    row["timestamp"]
                ).to_pydatetime()

                stmt = insert(
                    AirQualityRecord
                ).values(**row)

                stmt = stmt.on_conflict_do_update(

                    index_elements=[
                        "city",
                        "timestamp"
                    ],

                    set_={
                        col: getattr(
                            stmt.excluded,
                            col
                        )
                        for col in [
                            "latitude",
                            "longitude",
                            *POLLUTANTS
                        ]
                    }
                )

                db.execute(stmt)

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

            logging.info(
                "Database loading completed and oldest day purged: %d records",
                len(valid)
            )

            return len(valid)

        except Exception:

            db.rollback()

            logging.exception(
                "Database loading failed"
            )

            raise


# --------------------------------------------------
# 5. RUN COMPLETE ETL PIPELINE
# --------------------------------------------------

def run_etl():

    # Create required folders
    RAW.mkdir(
        parents=True,
        exist_ok=True
    )

    PROCESSED.mkdir(
        parents=True,
        exist_ok=True
    )

    # Create database tables
    Base.metadata.create_all(engine)

    frames = []
    errors = []

    # Extract data for all five cities
    for city, coords in CITIES.items():

        try:

            logging.info(
                "Starting extraction for %s",
                city
            )

            data = fetch_city(
                city,
                coords
            )

            # Save individual raw CSV
            raw_file = RAW / f"{city.lower()}_raw.csv"

            data.to_csv(
                raw_file,
                index=False
            )

            frames.append(data)

            time.sleep(0.15)

        except Exception as exc:

            logging.exception(
                "Extraction failed for %s",
                city
            )

            errors.append({
                "city": city,
                "error": str(exc)
            })

    # Stop if every city failed
    if not frames:

        return {
            "status": "error",
            "message": "No city data fetched. Check API or internet connection.",
            "errors": errors
        }

    # Combine all city data
    raw = pd.concat(
        frames,
        ignore_index=True
    )

    # Clean data
    cleaned = clean_data(raw)

    # Validate data
    valid, rejected = validate_rows(cleaned)

    # Save processed CSV
    if valid:

        processed_df = pd.DataFrame(valid)

        processed_df.to_csv(
            PROCESSED / "air_quality_cleaned.csv",
            index=False
        )

    # Load into database
    loaded_rows = load_to_database(valid)

    # Prepare pipeline summary
    result = {
        "status": (
            "partial" if errors
            else "success"
        ),

        "fetched_rows": len(raw),

        "cleaned_rows": len(cleaned),

        "valid_rows": len(valid),

        "rejected_rows": rejected,

        "database_rows_loaded": loaded_rows,

        "cities_succeeded": [
            frame["city"].iloc[0]
            for frame in frames
        ],

        "errors": errors,

        "completed_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    logging.info(
        "ETL pipeline completed: %s",
        result
    )

    return result
