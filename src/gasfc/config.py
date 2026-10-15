"""Shared constants: paths, LDZ codes and National Gas publication object IDs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
# committed outputs: what the dashboard and the daily job need without rerunning the pipeline
RESULTS = ROOT / "results"  # backtest predictions and the population map
MONITORING = ROOT / "monitoring"  # live forecasts and their scores, appended daily
CHAMPION_DIR = ROOT / "models" / "champion"  # the registered champion, exported for deployment

# The 13 Local Distribution Zones, in National Gas publication order.
LDZS = ["EA", "EM", "NE", "NO", "NT", "NW", "SC", "SE", "SO", "SW", "WM", "WN", "WS"]

LDZ_NAMES = {
    "EA": "East Anglia",
    "EM": "East Midlands",
    "NE": "North East",
    "NO": "Northern",
    "NT": "North Thames",
    "NW": "North West",
    "SC": "Scotland",
    "SE": "South East",
    "SO": "Southern",
    "SW": "South West",
    "WM": "West Midlands",
    "WN": "Wales North",
    "WS": "Wales South",
}

# National Gas Data Portal publication objects (Find Gas Data). Demand is in mcm/day.
# The LDZ is parsed from each row's data item name, so only the ID lists matter here.
SERIES = {
    "demand_actual_d1": [f"PUBOB{i}" for i in range(624, 637)],  # first actual, published D+1
    "demand_actual_d6": [f"PUBOB{i}" for i in range(639, 652)],  # closed-out actual, D+6
    "demand_forecast": [f"PUBOB{i}" for i in range(609, 622)],  # National Gas forecast, all vintages
    "cwv_actual": [f"PUBOB{i}" for i in range(3700, 3713)],  # composite weather variable, actual
    "cwv_forecast_d1": [f"PUBOB{i}" for i in range(3726, 3739)],  # CWV forecast issued the day before
}

# Data before this date has rolled off the portal's 5-year retention.
HISTORY_START = "2021-11-01"
