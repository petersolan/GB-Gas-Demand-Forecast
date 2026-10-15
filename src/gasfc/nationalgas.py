"""Download and tidy LDZ demand and weather data from the National Gas Data Portal.

The portal's Find Gas Data download returns CSV for a list of publication object IDs and a gas-day
range. Raw responses are kept as monthly CSV files because the portal only retains about five years:
the archive is what makes the history reproducible after it rolls off.
"""

import io
import re
import time
from datetime import date

import pandas as pd
import requests

from gasfc.config import RAW, SERIES
from gasfc.quality import choose_target

URL = "https://data.nationalgas.com/api/find-gas-data-download"
LDZ_RE = re.compile(r"LDZ ?\((\w{2})\)")
COLUMNS = ["gas_day", "ldz", "item", "value", "applicable_at", "generated_at"]


def fetch(ids: list[str], date_from: str, date_to: str, latest: bool) -> str:
    """One request to the portal; returns the CSV text."""
    params = {
        "applicableFor": "Y",
        "dateFrom": date_from,
        "dateTo": date_to,
        "dateType": "GASDAY",
        "latestFlag": "Y" if latest else "N",
        "ids": ",".join(ids),
        "type": "CSV",
    }
    for attempt in range(4):
        try:
            r = requests.get(URL, params=params, timeout=120)
            r.raise_for_status()
            return r.text
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def parse(csv_text: str) -> pd.DataFrame:
    """Portal CSV -> tidy rows: gas_day, ldz, item, value, applicable_at, generated_at."""
    df = pd.read_csv(io.StringIO(csv_text))
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    out = pd.DataFrame(
        {
            "gas_day": pd.to_datetime(df["Applicable For"], format="%d/%m/%Y"),
            "ldz": df["Data Item"].str.extract(LDZ_RE, expand=False),
            "item": df["Data Item"],
            "value": pd.to_numeric(df["Value"], errors="coerce"),
            "applicable_at": pd.to_datetime(df["Applicable At"], format="%d/%m/%Y %H:%M:%S"),
            "generated_at": pd.to_datetime(df["Generated Time"], format="%d/%m/%Y %H:%M:%S"),
        }
    )
    if out["ldz"].isna().any():
        bad = out.loc[out["ldz"].isna(), "item"].unique()[:3]
        raise ValueError(f"could not parse LDZ from items: {bad}")
    return out


def month_starts(start: str, end: date) -> list[pd.Timestamp]:
    return list(pd.date_range(pd.Timestamp(start).replace(day=1), pd.Timestamp(end), freq="MS"))


def download(series: str, start: str, end: date, refresh_last: int = 2) -> None:
    """Archive one series month by month under data/raw/<series>/YYYY-MM.csv.

    Months already archived are skipped, except the last `refresh_last` months, which may still be
    receiving values (D+6 closeouts, late forecasts).
    """
    folder = RAW / series
    folder.mkdir(parents=True, exist_ok=True)
    months = month_starts(start, end)
    latest = series != "demand_forecast"  # forecasts: keep every vintage, the benchmark needs D-1
    for i, m in enumerate(months):
        path = folder / f"{m:%Y-%m}.csv"
        if path.exists() and i < len(months) - refresh_last:
            continue
        m_end = min(m + pd.offsets.MonthEnd(0), pd.Timestamp(end))
        text = fetch(SERIES[series], f"{m:%Y-%m-%d}", f"{m_end:%Y-%m-%d}", latest)
        path.write_text(text, encoding="utf-8")


def load(series: str) -> pd.DataFrame:
    """All archived months of a series as one tidy frame."""
    files = sorted((RAW / series).glob("*.csv"))
    frames = [parse(f.read_text(encoding="utf-8")) for f in files]
    return pd.concat([f for f in frames if not f.empty], ignore_index=True)


def day_ahead_forecast(fc: pd.DataFrame, cutoff_hour: int = 14) -> pd.DataFrame:
    """National Gas's day-ahead forecast: the latest vintage issued before cutoff_hour on D-1.

    The day-ahead forecast is the fair benchmark for a model that runs on the afternoon before the
    gas day; the final within-day vintage already knows most of the day's weather.
    """
    cutoff = fc["gas_day"] - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    eligible = fc[fc["applicable_at"] <= cutoff]
    idx = eligible.groupby(["gas_day", "ldz"])["applicable_at"].idxmax()
    out = eligible.loc[idx, ["gas_day", "ldz", "value"]].rename(columns={"value": "ng_forecast_da"})
    # a few published forecasts are 0: treat them as missing, so the correction model falls back on
    # weather and lags instead of trusting them, and the benchmark is not scored on a broken value
    out["ng_forecast_da"] = out["ng_forecast_da"].where(out["ng_forecast_da"] > 0)
    return out


def latest_value(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Last published value per gas day and LDZ."""
    df = df.sort_values("generated_at").drop_duplicates(["gas_day", "ldz"], keep="last")
    return df[["gas_day", "ldz", "value"]].rename(columns={"value": name})


def build_daily() -> pd.DataFrame:
    """One row per gas day and LDZ: actual demand, CWVs and the National Gas day-ahead forecast."""
    daily = latest_value(load("demand_actual_d1"), "demand_d1")
    others = [
        latest_value(load("demand_actual_d6"), "demand_d6"),
        latest_value(load("cwv_actual"), "cwv_actual"),
        latest_value(load("cwv_forecast_d1"), "cwv_forecast_d1"),
        day_ahead_forecast(load("demand_forecast")),
    ]
    for other in others:
        daily = daily.merge(other, on=["gas_day", "ldz"], how="left")
    daily = choose_target(daily)
    return daily.sort_values(["ldz", "gas_day"]).reset_index(drop=True)
