# SE4GEO Air Quality Dashboard

This repository contains a collaborative 2025 software-engineering project for
exploring air-quality sensor measurements from the Lombardy Open Data portal.
The system combines:

- a PostgreSQL/PostGIS database for stations and measurements;
- a Python ingestion and daily-aggregation workflow;
- a Flask REST API;
- an interactive Dash/Plotly map and time-series interface.

It is an educational local application rather than a deployed monitoring
service. The repository preserves the original requirements and design
documents in [`docs/`](docs/).

## Architecture

```text
Dati Lombardia CSV files
          |
          v
     manage_data.py
          |
          v
 PostgreSQL + PostGIS <--- app.py (Flask REST API)
                                |
                                v
                        dash_app.py (Dash UI)
```

## Data sources

- [Air-quality measurements](https://www.dati.lombardia.it/Ambiente/Dati-sensori-aria-dal-2018/g2hp-ar79)
- [Station and sensor metadata](https://www.dati.lombardia.it/Ambiente/Stazioni-qualita-dell-aria/ib47-atvt)

The original analysis retained records before 2024. This remains the default
in `manage_data.py` and can be changed with `--before-year`.

## Local setup

Python 3.10 or newer and PostgreSQL with PostGIS are required.

```bash
git clone https://github.com/Hodamt/Software-Engineering.git
cd Software-Engineering
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy the environment template and set the database password locally:

```bash
cp .env.example .env
```

`.env` is ignored by Git. Database credentials must never be committed.
PostgreSQL service files or `.pgpass` can also provide the password.

Create a database and user matching `.env`, then enable the schema:

```sql
CREATE USER se4geo WITH PASSWORD 'choose-a-local-password';
CREATE DATABASE se4geo OWNER se4geo;
```

```bash
python create_table.py
```

Use `python create_table.py --reset` only when existing project tables and
their imported data should be deleted and recreated.

Download the two source CSV files and import them with explicit paths:

```bash
python manage_data.py \
  --sensors-csv data/stations.csv \
  --measurements-csv data/measurements.csv
```

Start the API and dashboard in separate terminals:

```bash
python app.py
python dash_app.py
```

The defaults are `http://localhost:5000/api` for the API and
`http://localhost:8050` for the dashboard.

Run the data-preparation tests with:

```bash
python -m unittest discover -s tests -v
```

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/sensors` | List station and sensor locations |
| `GET /api/sensors/<id>` | Return one sensor |
| `GET /api/pollutants` | List available pollutant names |
| `GET /api/date_range` | Return first and last imported dates |
| `GET /api/raw_measurements` | Query hourly measurements |
| `GET /api/measurements` | Query daily aggregates |
| `GET /api/sensors/<id>/measurements` | Query daily values for one sensor |

Measurement endpoints accept `sensor_id`, `pollutant`, `start`, and `end`
where applicable.

## Repository structure

```text
.
|-- app.py               # Flask API
|-- config.py            # Environment-based settings
|-- create_table.py      # PostGIS schema creation
|-- data_prep.py         # Testable CSV transformations
|-- manage_data.py       # CSV ingestion and aggregation
|-- dash_app.py          # Dash interface
|-- docs/                # Requirements and design documents
|-- .env.example         # Safe configuration template
`-- requirements.txt     # Python dependencies
```

## Scope and limitations

- The project has no user authentication and is intended for local use.
- CORS defaults to the local dashboard origin only.
- The source datasets can be large; ingestion currently loads each CSV into
  memory before bulk database insertion.
- The project does not interpolate missing values or provide regulatory alerts.
- No software licence has been added because this is collaborative coursework;
  reuse terms should be agreed by all contributors.

## Contributors

- Sadra Zahed Kachaee
- Hananeh Asadi Aghbolaghi
- Hoda Sadat Mousavi Tabar
- Firoozeh Rahimian
