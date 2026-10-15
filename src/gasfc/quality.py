"""Choose a trustworthy demand value per gas day and LDZ, and flag days where none is plausible.

Two actuals are published per day: a first value at D+1 and a closed-out value at D+6. Either can be
wrong: placeholder values repeated for days (e.g. 3.7 or 14.6 mcm), D+6 closeouts near zero or
negative, or runs of implausibly low readings. Gas demand is driven by weather, so each value is
compared with the median demand seen at the same weather (CWV) in the same LDZ, weekdays and weekends
separately. The closed-out value is preferred when plausible, then the first value; otherwise the day is
flagged and kept out of training and evaluation.
"""

import numpy as np
import pandas as pd

LOW, HIGH = 0.6, 1.6  # plausible range as a ratio of weather-expected demand


def expected_demand(df: pd.DataFrame, bin_width: float = 0.5) -> pd.Series:
    """Median demand at similar weather: same LDZ, CWV bin and weekday/weekend."""
    key = pd.DataFrame(
        {
            "ldz": df["ldz"],
            "cwv_bin": (df["cwv_actual"] / bin_width).round(),
            "weekend": df["gas_day"].dt.dayofweek >= 5,
        }
    )
    both = pd.concat([df["demand_d1"], df["demand_d6"]], axis=1).median(axis=1)
    return both.groupby([key["ldz"], key["cwv_bin"], key["weekend"]]).transform("median")


def level_shift(df: pd.DataFrame, window: int = 28, tolerance: float = 0.15) -> pd.Series:
    """True where actuals drift away from National Gas's own forecast for weeks at a time.

    A single bad day is caught by the weather check; a sustained under- or over-reading (a metering
    or allocation problem) shifts the weather relationship itself, so it is caught against an
    independent reference instead: the rolling median of forecast / actual, per LDZ.
    """
    ratio = df["ng_forecast_da"] / df["demand"]
    rolling = ratio.groupby(df["ldz"]).transform(
        lambda s: s.rolling(window, center=True, min_periods=window // 2).median()
    )
    return (rolling - 1).abs() > tolerance


def choose_target(df: pd.DataFrame) -> pd.DataFrame:
    """Add expected_demand, demand (chosen value or NaN) and demand_source.

    demand_source: d6 or d1 (the value used), flagged (neither plausible for the weather) or
    level_shift (inside a sustained drift from the operator's forecast).
    """
    out = df.sort_values(["ldz", "gas_day"]).copy()
    out["expected_demand"] = expected_demand(out)
    ok = {}
    for col in ("demand_d6", "demand_d1"):
        ratio = out[col] / out["expected_demand"]
        ok[col] = ratio.between(LOW, HIGH)
    out["demand_source"] = np.select([ok["demand_d6"], ok["demand_d1"]], ["d6", "d1"], default="flagged")
    out["demand"] = np.select(
        [ok["demand_d6"], ok["demand_d1"]], [out["demand_d6"], out["demand_d1"]], default=np.nan
    )
    if "ng_forecast_da" in out:
        shifted = level_shift(out) & out["demand"].notna()
        out.loc[shifted, "demand_source"] = "level_shift"
        out.loc[shifted, "demand"] = np.nan
    return out
