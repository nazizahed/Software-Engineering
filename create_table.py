"""Create the SE4GEO PostGIS schema."""

import argparse

import psycopg2

from config import database_connection_kwargs


DROP_ORDER = ["sensor_pollutants", "measurements", "raw_measurements", "sensors"]


def create_schema(reset: bool = False) -> None:
    with psycopg2.connect(**database_connection_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            if reset:
                for table in DROP_ORDER:
                    cursor.execute(f"DROP TABLE IF EXISTS {table};")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sensors (
                    sensor_id VARCHAR(50) PRIMARY KEY,
                    station_name VARCHAR(100) NOT NULL,
                    province VARCHAR(50),
                    latitude DOUBLE PRECISION NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    geom GEOMETRY(Point, 4326)
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_measurements (
                    measurement_id SERIAL PRIMARY KEY,
                    sensor_id VARCHAR(50) REFERENCES sensors(sensor_id),
                    timestamp TIMESTAMP NOT NULL,
                    pollutant VARCHAR(50) NOT NULL,
                    value DOUBLE PRECISION
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS measurements (
                    measurement_id SERIAL PRIMARY KEY,
                    sensor_id VARCHAR(50) REFERENCES sensors(sensor_id),
                    timestamp DATE NOT NULL,
                    pollutant VARCHAR(50) NOT NULL,
                    daily_avg DOUBLE PRECISION,
                    daily_min DOUBLE PRECISION,
                    daily_max DOUBLE PRECISION
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_pollutants (
                    sensor_id VARCHAR(50) REFERENCES sensors(sensor_id),
                    pollutant VARCHAR(50),
                    PRIMARY KEY (sensor_id, pollutant)
                );
                """
            )
    print("Database schema is ready.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the four project tables and recreate them. This removes imported data.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    create_schema(reset=arguments.reset)
