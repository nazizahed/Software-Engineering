"""Flask REST API for the SE4GEO air-quality database."""

import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2

from config import database_connection_kwargs, settings


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": list(settings.cors_origins)}})
logging.basicConfig(level=logging.INFO)


def get_db_connection():
    return psycopg2.connect(**database_connection_kwargs())


def _database_error(message: str, error: Exception):
    logging.exception(message, exc_info=error)
    return jsonify({"error": "database query failed"}), 500


@app.route("/api/sensors", methods=["GET"])
def list_sensors():
    try:
        with get_db_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sensor_id, station_name, province, latitude, longitude,
                       ST_AsGeoJSON(geom)::json AS geometry
                FROM sensors
                ORDER BY station_name, sensor_id;
                """
            )
            columns = [column[0] for column in cursor.description]
            sensors = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(sensors)
    except Exception as error:
        return _database_error("Failed to fetch sensors", error)


@app.route("/api/sensors/<sensor_id>", methods=["GET"])
def get_sensor(sensor_id):
    try:
        with get_db_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT sensor_id, station_name, province, latitude, longitude,
                       ST_AsGeoJSON(geom)::json AS geometry
                FROM sensors
                WHERE sensor_id = %s;
                """,
                (sensor_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return jsonify({"error": "sensor not found"}), 404
        keys = ["sensor_id", "station_name", "province", "latitude", "longitude", "geometry"]
        return jsonify(dict(zip(keys, row)))
    except Exception as error:
        return _database_error(f"Failed to fetch sensor {sensor_id}", error)


@app.route("/api/pollutants", methods=["GET"])
def list_pollutants():
    try:
        with get_db_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT pollutant FROM sensor_pollutants ORDER BY pollutant;")
            pollutants = [row[0] for row in cursor.fetchall()]
        return jsonify(pollutants)
    except Exception as error:
        return _database_error("Failed to fetch pollutants", error)


@app.route("/api/date_range", methods=["GET"])
def get_date_range():
    try:
        with get_db_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT MIN(timestamp)::date AS first_date,
                       MAX(timestamp)::date AS last_date
                FROM raw_measurements;
                """
            )
            first_date, last_date = cursor.fetchone()
        return jsonify(
            {
                "first_date": first_date.isoformat() if first_date else None,
                "last_date": last_date.isoformat() if last_date else None,
            }
        )
    except Exception as error:
        return _database_error("Failed to fetch date range", error)


def _measurement_filters():
    filters: list[str] = []
    parameters: list[str] = []
    values = {
        "sensor_id": request.args.get("sensor_id"),
        "pollutant": request.args.get("pollutant"),
        "start": request.args.get("start"),
        "end": request.args.get("end"),
    }
    if values["sensor_id"]:
        filters.append("sensor_id = %s")
        parameters.append(values["sensor_id"])
    if values["pollutant"]:
        filters.append("pollutant = %s")
        parameters.append(values["pollutant"])
    if values["start"]:
        filters.append("timestamp >= %s")
        parameters.append(values["start"])
    if values["end"]:
        filters.append("timestamp < %s::date + INTERVAL '1 day'")
        parameters.append(values["end"])
    return filters, parameters


@app.route("/api/raw_measurements", methods=["GET"])
def list_raw_measurements():
    filters, parameters = _measurement_filters()
    where = "WHERE " + " AND ".join(filters) if filters else ""
    query = f"""
        SELECT measurement_id, sensor_id,
               to_char(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS') AS timestamp,
               pollutant, value
        FROM raw_measurements
        {where}
        ORDER BY timestamp;
    """
    try:
        with get_db_connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, parameters)
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(rows)
    except Exception as error:
        return _database_error("Failed to fetch raw measurements", error)


@app.route("/api/measurements", methods=["GET"])
def list_measurements():
    filters, parameters = _measurement_filters()
    where = "WHERE " + " AND ".join(filters) if filters else ""
    query = f"""
        SELECT sensor_id, timestamp::text AS date, pollutant,
               daily_avg, daily_min, daily_max
        FROM measurements
        {where}
        ORDER BY date;
    """
    try:
        with get_db_connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, parameters)
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(rows)
    except Exception as error:
        return _database_error("Failed to fetch daily measurements", error)


@app.route("/api/sensors/<sensor_id>/measurements", methods=["GET"])
def measurements_by_sensor(sensor_id):
    start = request.args.get("start")
    end = request.args.get("end")
    filters = ["sensor_id = %s"]
    parameters = [sensor_id]
    if start:
        filters.append("timestamp >= %s")
        parameters.append(start)
    if end:
        filters.append("timestamp < %s::date + INTERVAL '1 day'")
        parameters.append(end)
    query = f"""
        SELECT timestamp::text AS date, pollutant, daily_avg, daily_min, daily_max
        FROM measurements
        WHERE {' AND '.join(filters)}
        ORDER BY date;
    """
    try:
        with get_db_connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, parameters)
            columns = [column[0] for column in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if not rows:
            return jsonify({"error": "no measurements found"}), 404
        return jsonify(rows)
    except Exception as error:
        return _database_error(f"Failed to fetch measurements for sensor {sensor_id}", error)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=settings.flask_debug)
