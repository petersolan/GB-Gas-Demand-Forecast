"""Day-ahead forecast for tomorrow's gas day with the champion model.

Run in the afternoon (after National Gas publishes yesterday's actuals and the CWV forecast):
refreshes the data, builds tomorrow's feature rows and appends the forecast to
data/processed/forecasts.parquet, so forecasts can be scored once the actuals arrive.

    python scripts/06_forecast.py
"""

from datetime import date, timedelta

import mlflow
import pandas as pd

from gasfc.config import HISTORY_START, LDZS, PROCESSED, SERIES
from gasfc.features import build
from gasfc.nationalgas import build_daily, day_ahead_forecast, download, latest_value, load
from gasfc.tracking import MODEL_NAME, setup
from gasfc.weather import download_points, ldz_weather


def main() -> None:
    today = date.today()
    target = pd.Timestamp(today + timedelta(days=1))
    for series in SERIES:
        download(series, HISTORY_START, today + timedelta(days=1))
    daily = build_daily()
    daily.to_parquet(PROCESSED / "ldz_daily.parquet", index=False)

    # tomorrow has no actuals yet: add its rows with what National Gas published today, the CWV
    # forecast and its own day-ahead demand forecast (latest vintage before the 14:00 cutoff)
    cwv = latest_value(load("cwv_forecast_d1"), "cwv_forecast_d1")
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

    points = pd.read_parquet(PROCESSED / "weather_points.parquet")
    download_points(points, HISTORY_START, (target + pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    weather = ldz_weather(points)
    weather.to_parquet(PROCESSED / "ldz_weather.parquet", index=False)
    rows = build(daily, weather)
    rows = rows[rows["gas_day"] == target]

    setup("gas-demand-training")
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@champion")
    fc = model.predict(rows)
    fc["issued_at"] = pd.Timestamp.now().floor("s")
    print(fc.round(2).to_string(index=False))

    path = PROCESSED / "forecasts.parquet"
    history = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    pd.concat([history, fc], ignore_index=True).to_parquet(path, index=False)


if __name__ == "__main__":
    main()
