"""Pure pandas transformations for the Lombardy source CSV files."""

from pathlib import Path

import pandas as pd


def normalize_sensor_ids(values: pd.Series) -> pd.Series:
    """Represent integer-like sensor identifiers consistently as strings."""
    return values.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()


def prepare_sensors(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.read_csv(path)
    required = {"IdSensore", "NomeStazione", "Provincia", "lat", "lng", "NomeTipoSensore"}
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"Sensor file is missing columns: {sorted(missing)}")

    sensors = source[["IdSensore", "NomeStazione", "Provincia", "lat", "lng"]].copy()
    sensors.columns = ["sensor_id", "station_name", "province", "latitude", "longitude"]
    sensors.dropna(subset=["latitude", "longitude"], inplace=True)
    sensors["sensor_id"] = normalize_sensor_ids(sensors["sensor_id"])
    sensors.drop_duplicates(subset=["sensor_id"], inplace=True)

    pollutants = source[["IdSensore", "NomeTipoSensore"]].copy()
    pollutants.columns = ["sensor_id", "pollutant"]
    pollutants["sensor_id"] = normalize_sensor_ids(pollutants["sensor_id"])
    pollutants.dropna(subset=["pollutant"], inplace=True)
    pollutants.drop_duplicates(inplace=True)
    return sensors, pollutants


def prepare_measurements(
    path: Path,
    sensor_pollutants: pd.DataFrame,
    before_year: int | None,
) -> pd.DataFrame:
    measurements = pd.read_csv(path)
    measurements.columns = measurements.columns.str.strip()
    required = {"idSensore", "Valore", "Data"}
    missing = required.difference(measurements.columns)
    if missing:
        raise ValueError(f"Measurement file is missing columns: {sorted(missing)}")

    measurements["timestamp"] = pd.to_datetime(
        measurements["Data"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
    )
    measurements.rename(columns={"idSensore": "sensor_id", "Valore": "value"}, inplace=True)
    measurements.dropna(subset=["sensor_id", "value", "timestamp"], inplace=True)
    measurements["sensor_id"] = normalize_sensor_ids(measurements["sensor_id"])
    measurements["value"] = pd.to_numeric(measurements["value"], errors="coerce")
    measurements.dropna(subset=["value"], inplace=True)
    measurements = measurements[measurements["value"] >= 0]
    if before_year is not None:
        measurements = measurements[measurements["timestamp"].dt.year < before_year]

    merged = measurements.merge(sensor_pollutants, on="sensor_id", how="left")
    merged.dropna(subset=["pollutant"], inplace=True)
    if merged.empty:
        raise ValueError("No valid measurement rows remained after cleaning and sensor matching")
    return merged

