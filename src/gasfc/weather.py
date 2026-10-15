"""Population-weighted weather per LDZ and gas day from Open-Meteo.

The Previous Runs API keeps what forecasts said one day before (`*_previous_day1`) from early 2024,
alongside the latest forecast for each hour (`*`, effectively same-day weather). A day-ahead model must
only see the day-before forecast; earlier history has none, so training before 2024 falls back to the
same-day values and the column `weather_source` says which was used.

Hourly values are aggregated over the gas day, 05:00 to 05:00 UK local time, then weighted across each
LDZ's weather points by the share of its population they represent.
"""

import time

import pandas as pd
import requests

from gasfc.config import RAW

URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
VARIABLES = ["temperature_2m", "wind_speed_10m", "shortwave_radiation"]
GAS_DAY_START_HOUR = 5


def fetch_point(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """Hourly day-before and same-day values for one point, in UK local time."""
    hourly = VARIABLES + [f"{v}_previous_day1" for v in VARIABLES]
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(hourly),
        "timezone": "Europe/London",
    }
    for attempt in range(5):
        r = requests.get(URL, params=params, timeout=300)
        if r.status_code == 429:  # rate limited: back off and retry
            time.sleep(60 * (attempt + 1))
            continue
        r.raise_for_status()
        break
    else:
        raise RuntimeError("Open-Meteo rate limit not cleared")
    df = pd.DataFrame(r.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def gas_day(times: pd.Series) -> pd.Series:
    """Gas day of each local timestamp: hours before 05:00 belong to the previous gas day."""
    return (times - pd.Timedelta(hours=GAS_DAY_START_HOUR)).dt.normalize()


def daily_features(hourly: pd.DataFrame) -> pd.DataFrame:
    """Gas-day weather from hourly values, preferring the day-before forecast where it exists."""
    h = hourly.copy()
    h["gas_day"] = gas_day(h["time"])
    h["day_before"] = h[[f"{v}_previous_day1" for v in VARIABLES]].notna().all(axis=1)
    for v in VARIABLES:
        h[v] = h[f"{v}_previous_day1"].where(h["day_before"], h[v])
    g = h.groupby("gas_day")
    out = pd.DataFrame(
        {
            "temp_mean": g["temperature_2m"].mean(),
            "temp_min": g["temperature_2m"].min(),
            "temp_max": g["temperature_2m"].max(),
            "wind_mean": g["wind_speed_10m"].mean(),
            "solar_mean": g["shortwave_radiation"].mean(),
            "day_before_share": g["day_before"].mean(),
            "hours": g.size(),
        }
    )
    out = out[out["hours"] >= 23]  # drop part days at the ends (23 and 25 at clock changes)
    out["weather_source"] = (out.pop("day_before_share") == 1).map({True: "day_before", False: "same_day"})
    return out.drop(columns="hours").reset_index()


def download_points(points: pd.DataFrame, start: str, end: str) -> None:
    """Cache hourly weather per point as data/raw/weather/<ldz>_<point>.parquet."""
    folder = RAW / "weather"
    folder.mkdir(parents=True, exist_ok=True)
    for p in points.itertuples():
        path = folder / f"{p.ldz}_{p.point}.parquet"
        if not path.exists():
            fetch_point(p.latitude, p.longitude, start, end).to_parquet(path, index=False)
            continue
        cached = pd.read_parquet(path)
        have = cached["time"].max()
        if have >= pd.Timestamp(end) + pd.Timedelta(hours=23):
            continue
        # incremental: refetch the last few days (forecasts for recent days get replaced), then append
        since = (have - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
        fresh = fetch_point(p.latitude, p.longitude, since, end)
        merged = pd.concat([cached[cached["time"] < fresh["time"].min()], fresh], ignore_index=True)
        merged.to_parquet(path, index=False)


def ldz_weather(points: pd.DataFrame) -> pd.DataFrame:
    """Population-weighted gas-day weather per LDZ from the cached points."""
    frames = []
    for p in points.itertuples():
        d = daily_features(pd.read_parquet(RAW / "weather" / f"{p.ldz}_{p.point}.parquet"))
        d["ldz"], d["weight"] = p.ldz, p.weight
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    cols = ["temp_mean", "temp_min", "temp_max", "wind_mean", "solar_mean"]
    weighted = d[cols].mul(d["weight"], axis=0).assign(ldz=d["ldz"], gas_day=d["gas_day"])
    out = weighted.groupby(["ldz", "gas_day"])[cols].sum()
    # a gas day counts as day-before only if every point had the day-before forecast
    source = d.groupby(["ldz", "gas_day"])["weather_source"].agg(
        lambda s: s.mode()[0] if s.nunique() == 1 else "same_day"
    )
    return out.join(source).reset_index()
