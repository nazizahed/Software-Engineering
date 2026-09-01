"""Import Dati Lombardia station and measurement CSV files into PostGIS."""

import argparse
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from config import database_connection_kwargs
from data_prep import prepare_measurements, prepare_sensors


def import_data(sensors: pd.DataFrame, measurements: pd.DataFrame) -> None:
    sensor_rows = [
        (
            row.sensor_id,
            row.station_name,
            row.province,
            float(row.latitude),
            float(row.longitude),
            float(row.longitude),
            float(row.latitude),
        )
        for row in sensors.itertuples(index=False)
    ]
    raw_rows = [
        (row.sensor_id, row.timestamp, row.pollutant, float(row.value))
        for row in measurements.itertuples(index=False)
    ]

    daily = (
        measurements.assign(date=measurements["timestamp"].dt.date)
        .groupby(["sensor_id", "pollutant", "date"])["value"]
        .agg(daily_avg="mean", daily_min="min", daily_max="max")
        .reset_index()
    )
    daily_rows = [
        (
            row.sensor_id,
            row.date,
            row.pollutant,
            round(float(row.daily_avg), 3),
            round(float(row.daily_min), 3),
            round(float(row.daily_max), 3),
        )
        for row in daily.itertuples(index=False)
    ]
    pollutant_rows = list(
        measurements[["sensor_id", "pollutant"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )

    with psycopg2.connect(**database_connection_kwargs()) as connection:
        with connection.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO sensors
                    (sensor_id, station_name, province, latitude, longitude, geom)
                VALUES %s
                ON CONFLICT (sensor_id) DO UPDATE SET
                    station_name = EXCLUDED.station_name,
                    province = EXCLUDED.province,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    geom = EXCLUDED.geom;
                """,
                sensor_rows,
                template="(%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
                page_size=5000,
            )
            cursor.execute("DELETE FROM sensor_pollutants;")
            cursor.execute("DELETE FROM measurements;")
            cursor.execute("DELETE FROM raw_measurements;")
            execute_values(
                cursor,
                """
                INSERT INTO raw_measurements (sensor_id, timestamp, pollutant, value)
                VALUES %s;
                """,
                raw_rows,
                page_size=10000,
            )
            execute_values(
                cursor,
                """
                INSERT INTO measurements
                    (sensor_id, timestamp, pollutant, daily_avg, daily_min, daily_max)
                VALUES %s;
                """,
                daily_rows,
                page_size=10000,
            )
            execute_values(
                cursor,
                """
                INSERT INTO sensor_pollutants (sensor_id, pollutant)
                VALUES %s ON CONFLICT DO NOTHING;
                """,
                pollutant_rows,
                page_size=5000,
            )
    print(
        f"Imported {len(sensors):,} sensors, {len(raw_rows):,} hourly records, "
        f"and {len(daily_rows):,} daily aggregates."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensors-csv", required=True, type=Path)
    parser.add_argument("--measurements-csv", required=True, type=Path)
    parser.add_argument(
        "--before-year",
        type=int,
        default=2024,
        help="Keep records before this year, matching the original project scope. Use 0 for all years.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    sensor_frame, sensor_pollutant_frame = prepare_sensors(arguments.sensors_csv)
    measurement_frame = prepare_measurements(
        arguments.measurements_csv,
        sensor_pollutant_frame,
        before_year=arguments.before_year or None,
    )
    import_data(sensor_frame, measurement_frame)
