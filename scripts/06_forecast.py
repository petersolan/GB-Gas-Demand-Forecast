"""Day-ahead forecast for tomorrow's gas day with the champion model.

Run in the afternoon (after National Gas publishes yesterday's actuals and its day-ahead forecast):
refreshes the data, builds tomorrow's feature rows and appends the forecast to
monitoring/forecasts.csv, so it can be scored once the actuals arrive (scripts/07_score.py).

    python scripts/06_forecast.py                                      # registry champion, full history
    python scripts/06_forecast.py --model models/champion --history-days 90   # what the daily job runs

Features look back at most 8 days and the quality checks about 4 weeks, so 90 days of history is
enough for a forecast; the daily GitHub Action uses that and the exported champion, with no registry.
"""

import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import mlflow
import pandas as pd

from gasfc.config import HISTORY_START, LDZS, MONITORING, PROCESSED, ROOT, SERIES
from gasfc.features import build
from gasfc.nationalgas import as_of_cutoff, build_daily, day_ahead_forecast, download, load
from gasfc.tracking import MODEL_NAME, setup
from gasfc.weather import download_points, ldz_weather

UK = ZoneInfo("Europe/London")
FORECASTS = MONITORING / "forecasts.csv"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=f"models:/{MODEL_NAME}@champion", help="model URI or folder")
    ap.add_argument("--history-days", type=int, help="download only this many recent days")
    a = ap.parse_args()

    now = datetime.now(UK)
    today = now.date()
    target = pd.Timestamp(today + timedelta(days=1))
    start = str(today - timedelta(days=a.history_days)) if a.history_days else HISTORY_START
    for series in SERIES:
        download(series, start, today + timedelta(days=1))
    PROCESSED.mkdir(parents=True, exist_ok=True)
    daily = build_daily()
    daily.to_parquet(PROCESSED / "ldz_daily.parquet", index=False)

    # tomorrow has no actuals yet: add its rows with what National Gas published today, the CWV
    # forecast and its own day-ahead demand forecast (latest versions before the 14:00 cutoff)
    cwv = as_of_cutoff(load("cwv_forecast_d1"), "cwv_forecast_d1")
    ng = day_ahead_forecast(load("demand_forecast"))
    future = (
        pd.DataFrame({"gas_day": target, "ldz": LDZS})
        .merge(cwv, on=["gas_day", "ldz"], how="left")
        .merge(ng, on=["gas_day", "ldz"], how="left")
    )
    for col in ("cwv_forecast_d1", "ng_forecast_da"):
        if future[col].isna().all():
            print(f"{col} for {target.date()} not published yet; the model will work without it")
    daily = pd.concat([daily[daily["gas_day"] < target], future], ignore_index=True)

    points_path = PROCESSED / "weather_points.parquet"
    if points_path.exists():
        points = pd.read_parquet(points_path)
    else:  # fresh checkout (the daily job): the committed points
        points = pd.read_csv(ROOT / "reference" / "weather_points.csv")
    download_points(points, start, (target + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    weather = ldz_weather(points)
    weather.to_parquet(PROCESSED / "ldz_weather.parquet", index=False)
    rows = build(daily, weather)
    rows = rows[rows["gas_day"] == target]

    if a.model.startswith("models:/"):
        setup("gas-demand-training")
    model = mlflow.pyfunc.load_model(a.model)
    fc = model.predict(rows).merge(rows[["gas_day", "ldz", "ng_forecast_da"]], on=["gas_day", "ldz"])
    fc["issued_at"] = pd.Timestamp(now.replace(tzinfo=None)).floor("s")
    print(fc.to_string(index=False, float_format="%.2f"))

    # one forecast per gas day: a rerun later in the day would see more than the 14:00 forecast did
    history = pd.read_csv(FORECASTS, parse_dates=["gas_day", "issued_at"]) if FORECASTS.exists() else None
    out = pd.concat([history, fc], ignore_index=True).drop_duplicates(["gas_day", "ldz"], keep="first")
    out = out.sort_values(["gas_day", "ldz"])
    values = ["forecast", "p10", "p90", "ng_forecast_da"]
    out[values] = out[values].round(3)
    out["gas_day"] = out["gas_day"].dt.strftime("%Y-%m-%d")
    MONITORING.mkdir(exist_ok=True)
    out.to_csv(FORECASTS, index=False)


if __name__ == "__main__":
    main()
