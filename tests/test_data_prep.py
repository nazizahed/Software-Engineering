import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data_prep import prepare_measurements, prepare_sensors


class DataPreparationTests(unittest.TestCase):
    def test_sensor_ids_and_measurement_filters_are_consistent(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            sensors_path = directory / "sensors.csv"
            measurements_path = directory / "measurements.csv"
            pd.DataFrame(
                {
                    "IdSensore": [101],
                    "NomeStazione": ["Example station"],
                    "Provincia": ["MI"],
                    "lat": [45.46],
                    "lng": [9.19],
                    "NomeTipoSensore": ["PM10"],
                }
            ).to_csv(sensors_path, index=False)
            pd.DataFrame(
                {
                    "idSensore": [101.0, 101.0, 101.0],
                    "Valore": [12.5, -9999, 20.0],
                    "Data": [
                        "01/01/2023 12:00:00",
                        "02/01/2023 12:00:00",
                        "01/01/2024 12:00:00",
                    ],
                }
            ).to_csv(measurements_path, index=False)

            sensors, pollutants = prepare_sensors(sensors_path)
            measurements = prepare_measurements(measurements_path, pollutants, before_year=2024)

            self.assertEqual(sensors["sensor_id"].tolist(), ["101"])
            self.assertEqual(measurements["sensor_id"].tolist(), ["101"])
            self.assertEqual(measurements["pollutant"].tolist(), ["PM10"])
            self.assertEqual(measurements["value"].tolist(), [12.5])

    def test_missing_sensor_columns_raise_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sensors.csv"
            pd.DataFrame({"IdSensore": [1]}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "missing columns"):
                prepare_sensors(path)


if __name__ == "__main__":
    unittest.main()
