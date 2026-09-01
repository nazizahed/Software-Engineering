"""Dash interface for the SE4GEO air-quality API."""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import requests

from config import settings


API_BASE = settings.api_base_url
SESSION = requests.Session()


def _get_json(path: str, **kwargs):
    response = SESSION.get(f"{API_BASE}/{path.lstrip('/')}", timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def fetch_initial_data():
    pollutants = _get_json("pollutants")
    sensors = _get_json("sensors")
    date_range = _get_json("date_range")
    if not pollutants or not sensors or not date_range.get("first_date"):
        raise RuntimeError("The API returned no imported air-quality data")
    return pollutants, sensors, date_range


try:
    POLLUTANTS, SENSORS, DATE_RANGE = fetch_initial_data()
except (requests.RequestException, RuntimeError) as error:
    raise RuntimeError(
        f"Could not initialize the dashboard from {API_BASE}. "
        "Start app.py after creating and populating the database."
    ) from error


app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(
    [
        html.Header(
            html.H1("Lombardy Air Quality Dashboard"),
            style={"textAlign": "center", "padding": "20px 0", "backgroundColor": "#f8f9fa"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Select pollutant"),
                        dcc.Dropdown(
                            id="map-pollutant",
                            options=[{"label": value, "value": value} for value in POLLUTANTS],
                            value=POLLUTANTS[0],
                            clearable=False,
                        ),
                        html.Br(),
                        html.Label("Select date"),
                        dcc.DatePickerSingle(id="map-date", date=DATE_RANGE["last_date"]),
                    ],
                    style={"width": "30%", "padding": "10px"},
                ),
                html.Div(
                    dcc.Graph(id="map-graph", config={"displayModeBar": False}),
                    style={"width": "70%", "padding": "10px"},
                ),
            ],
            style={"display": "flex", "backgroundColor": "#ffffff", "padding": "10px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Select sensor"),
                        dcc.Dropdown(
                            id="ts-sensor",
                            options=[
                                {"label": sensor["station_name"], "value": sensor["sensor_id"]}
                                for sensor in SENSORS
                            ],
                            value=SENSORS[0]["sensor_id"],
                            clearable=False,
                        ),
                        html.Br(),
                        html.Label("Select date range"),
                        dcc.DatePickerRange(
                            id="ts-range",
                            min_date_allowed=DATE_RANGE["first_date"],
                            max_date_allowed=DATE_RANGE["last_date"],
                            start_date=DATE_RANGE["first_date"],
                            end_date=DATE_RANGE["last_date"],
                        ),
                    ],
                    style={"width": "30%", "padding": "10px"},
                ),
                html.Div(
                    dcc.Graph(id="ts-graph", config={"displayModeBar": False}),
                    style={"width": "70%", "padding": "10px"},
                ),
            ],
            style={"display": "flex", "backgroundColor": "#ffffff", "padding": "10px"},
        ),
    ]
)


@app.callback(
    Output("map-graph", "figure"),
    Input("map-pollutant", "value"),
    Input("map-date", "date"),
)
def update_map(pollutant, map_date):
    rows = _get_json(
        "measurements",
        params={"pollutant": pollutant, "start": map_date, "end": map_date},
    )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return px.scatter_mapbox(
            pd.DataFrame(columns=["latitude", "longitude", "daily_avg"]),
            lat="latitude",
            lon="longitude",
            zoom=6,
            mapbox_style="open-street-map",
            title=f"No data for {pollutant} on {map_date}",
        )
    frame = frame.merge(pd.DataFrame(SENSORS), on="sensor_id", how="left")
    return px.scatter_mapbox(
        frame,
        lat="latitude",
        lon="longitude",
        color="daily_avg",
        size="daily_avg",
        hover_name="station_name",
        hover_data={"daily_avg": ":.2f"},
        zoom=6,
        height=500,
        mapbox_style="open-street-map",
        title=f"{pollutant} on {map_date}",
    )


@app.callback(
    Output("ts-graph", "figure"),
    Input("ts-sensor", "value"),
    Input("ts-range", "start_date"),
    Input("ts-range", "end_date"),
)
def update_timeseries(sensor_id, start, end):
    rows = _get_json(
        "raw_measurements",
        params={"sensor_id": sensor_id, "start": start, "end": end},
    )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return px.line(title="No hourly data available for this range")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    figure = px.line(
        frame,
        x="timestamp",
        y="value",
        color="pollutant",
        title=f"Hourly measurements for sensor {sensor_id}",
    )
    figure.update_layout(xaxis_title="Timestamp", yaxis_title="Measured value")
    return figure


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
