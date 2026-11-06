
import logging
import sqlite3

import numpy as np
import pandas as pd

from .config import DB, REPORTS, POLLUTANTS


logging.basicConfig(level=logging.INFO)

# Columns to analyze
NUMERIC_COLUMNS = POLLUTANTS


# --------------------------------------------------
# 1. LOAD DATA FROM SQLITE DATABASE
# --------------------------------------------------

def load_data():

    REPORTS.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB) as connection:

        df = pd.read_sql_query(
            "SELECT * FROM air_quality_records",
            connection,
            parse_dates=["timestamp"]
        )

    if df.empty:
        raise ValueError("No records found in database.")

    logging.info("Loaded %d records", len(df))

    return df


# --------------------------------------------------
# 2. DESCRIPTIVE STATISTICS
# --------------------------------------------------

def descriptive_statistics(df):

    stats = df[NUMERIC_COLUMNS].describe().T

    stats.to_csv(
        REPORTS / "descriptive_statistics.csv"
    )

    return stats


# --------------------------------------------------
# 3. CITY-WISE POLLUTION COMPARISON
# --------------------------------------------------

def city_comparison(df):

    comparison = (
        df.groupby("city")[NUMERIC_COLUMNS]
        .mean()
        .round(2)
    )

    comparison.to_csv(
        REPORTS / "city_pollution_comparison.csv"
    )

    return comparison


# --------------------------------------------------
# 4. MAXIMUM AND MINIMUM POLLUTION
# --------------------------------------------------

def pollution_extremes(df):

    results = []

    for pollutant in NUMERIC_COLUMNS:

        valid = df.dropna(
            subset=[pollutant]
        )

        if valid.empty:
            continue

        maximum = valid.loc[
            valid[pollutant].idxmax()
        ]

        minimum = valid.loc[
            valid[pollutant].idxmin()
        ]

        results.append({

            "pollutant": pollutant,

            "maximum_value": maximum[pollutant],

            "maximum_city": maximum["city"],

            "maximum_time": maximum["timestamp"],

            "minimum_value": minimum[pollutant],

            "minimum_city": minimum["city"],

            "minimum_time": minimum["timestamp"]

        })

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        REPORTS / "pollution_extremes.csv",
        index=False
    )

    return result_df


# --------------------------------------------------
# 5. HOURLY POLLUTION TRENDS
# --------------------------------------------------

def hourly_trends(df):

    df = df.copy()

    df["hour"] = df["timestamp"].dt.hour

    trends = (
        df.groupby("hour")[NUMERIC_COLUMNS]
        .mean()
        .round(2)
    )

    trends.to_csv(
        REPORTS / "hourly_pollution_trends.csv"
    )

    return trends


# --------------------------------------------------
# 6. POLLUTANT CORRELATION MATRIX
# --------------------------------------------------

def correlation_analysis(df):

    correlation = (
        df[NUMERIC_COLUMNS]
        .corr(method="pearson")
        .round(3)
    )

    correlation.to_csv(
        REPORTS / "pollutant_correlation.csv"
    )

    return correlation


# --------------------------------------------------
# 7. OUTLIER DETECTION USING IQR
# --------------------------------------------------

def detect_outliers(df):

    results = []

    for pollutant in NUMERIC_COLUMNS:

        values = df[pollutant].dropna()

        if values.empty:
            continue

        q1 = values.quantile(0.25)

        q3 = values.quantile(0.75)

        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr

        upper_bound = q3 + 1.5 * iqr

        outliers = values[
            (values < lower_bound) |
            (values > upper_bound)
        ]

        results.append({

            "pollutant": pollutant,

            "Q1": q1,

            "Q3": q3,

            "IQR": iqr,

            "lower_bound": lower_bound,

            "upper_bound": upper_bound,

            "outlier_count": len(outliers),

            "outlier_percentage": round(
                len(outliers) / len(values) * 100,
                2
            )

        })

    result_df = pd.DataFrame(results)

    result_df.to_csv(
        REPORTS / "outlier_analysis.csv",
        index=False
    )

    return result_df


# --------------------------------------------------
# 8. RUN COMPLETE EDA PIPELINE
# --------------------------------------------------

def run_eda():

    df = load_data()

    logging.info("Starting EDA analysis")

    results = {}

    results["descriptive_statistics"] = (
        descriptive_statistics(df)
    )

    results["city_comparison"] = (
        city_comparison(df)
    )

    results["pollution_extremes"] = (
        pollution_extremes(df)
    )

    results["hourly_trends"] = (
        hourly_trends(df)
    )

    results["correlation"] = (
        correlation_analysis(df)
    )

    results["outliers"] = (
        detect_outliers(df)
    )

    summary = {

        "total_records": len(df),

        "total_cities": df["city"].nunique(),

        "cities": sorted(
            df["city"].unique().tolist()
        ),

        "pollutants_analyzed": len(NUMERIC_COLUMNS),

        "reports_generated": len(results)

    }

    logging.info("EDA completed: %s", summary)

    return summary


if __name__ == "__main__":

    print("\nSTARTING AIR QUALITY EDA\n")

    result = run_eda()

    print("\nEDA SUMMARY")

    print(result)

    print("\nREPORTS SAVED IN:")

    print(REPORTS)
