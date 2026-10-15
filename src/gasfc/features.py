"""Feature table for day-ahead forecasting: one row per LDZ and gas day.

Everything must be known at the forecast time, 14:00 on the day before the gas day (D-1):
- demand: the latest published actual is for D-2 (D+1 actuals appear around midday), so lags start at 2
- weather: day-before forecasts (National Gas CWV forecast and population-weighted Open-Meteo)
- calendar: weekday, bank holidays for the LDZ's nation, Christmas period, season
"""

import holidays
import numpy as np
import pandas as pd

LDZ_NATION = {"SC": "SCT", "WN": "WLS", "WS": "WLS"}  # all others England
HEATING_BASE_C = 15.5  # degree-day base temperature commonly used for UK heating demand

WEATHER = ["temp_mean", "temp_min", "temp_max", "wind_mean", "solar_mean"]
CALENDAR = ["dow", "is_weekend", "is_holiday", "christmas", "doy_sin", "doy_cos"]
# demand lags come with the weather of the same days, so the model can tell a cold-driven high from a
# change in the underlying level (prices, efficiency, a new large consumer)
LAGS = ["demand_lag2", "demand_lag7", "demand_mean_2_8", "cwv_actual_lag2", "cwv_actual_lag7"]
POP_WEATHER = WEATHER + ["hdd", "wind_chill", "temp_mean_prev", "temp_mean_prev2"]
CWV = ["cwv_forecast_d1"]
OPERATOR = ["ng_forecast_da"]  # National Gas's own day-ahead forecast, published before the gas day


def bank_holidays(nation: str, years: range) -> set[pd.Timestamp]:
    return {pd.Timestamp(d) for d in holidays.UK(subdiv=nation, years=years)}


def calendar(df: pd.DataFrame) -> pd.DataFrame:
    day = df["gas_day"]
    years = range(day.dt.year.min(), day.dt.year.max() + 2)
    hol = {n: bank_holidays(n, years) for n in ("ENG", "SCT", "WLS")}
    nation = df["ldz"].map(LDZ_NATION).fillna("ENG")
    doy = day.dt.dayofyear
    return pd.DataFrame(
        {
            "dow": day.dt.dayofweek,
            "is_weekend": (day.dt.dayofweek >= 5).astype(int),
            "is_holiday": [int(d in hol[n]) for d, n in zip(day, nation, strict=True)],
            "christmas": (
                (day.dt.month == 12) & (day.dt.day >= 24) | (day.dt.month == 1) & (day.dt.day <= 2)
            ).astype(int),
            "doy_sin": np.sin(2 * np.pi * doy / 365.25),
            "doy_cos": np.cos(2 * np.pi * doy / 365.25),
        },
        index=df.index,
    )


def build(daily: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Join demand, weather and calendar into the modelling table (rows for every LDZ and day)."""
    df = daily.merge(weather, on=["ldz", "gas_day"], how="left").sort_values(["ldz", "gas_day"])
    df = df.reset_index(drop=True)
    g = df.groupby("ldz")
    # lags use the first published actual (D+1): at 14:00 on D-1 the D+6 closeout of D-2 does not exist
    # yet. Days flagged by the quality checks stay NaN, which LightGBM handles natively.
    known = df["demand_d1"].where(df["demand"].notna())
    df["demand_lag2"] = known.groupby(df["ldz"]).shift(2)
    df["demand_lag7"] = known.groupby(df["ldz"]).shift(7)
    df["demand_mean_2_8"] = known.groupby(df["ldz"]).transform(
        lambda s: s.shift(2).rolling(7, min_periods=4).mean()
    )
    df["cwv_actual_lag2"] = g["cwv_actual"].shift(2)  # actual CWV is published at D+1, like demand
    df["cwv_actual_lag7"] = g["cwv_actual"].shift(7)
    df["hdd"] = (HEATING_BASE_C - df["temp_mean"]).clip(lower=0)
    df["wind_chill"] = df["hdd"] * np.sqrt(df["wind_mean"].clip(lower=0))
    df["temp_mean_prev"] = g["temp_mean"].shift(1)  # buildings cool slowly: yesterday's weather matters
    df["temp_mean_prev2"] = g["temp_mean"].shift(2)
    return pd.concat([df, calendar(df)], axis=1)
