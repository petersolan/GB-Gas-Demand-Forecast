"""Live monitoring: score the daily forecasts as actuals arrive and watch for drift.

The backtest says how the model would have done; this says how it is doing. Actual demand is the
quality-checked value (the D+1 first value, replaced by the D+6 closeout when it arrives), so the last
week's scores can still change: they are recomputed from scratch on every run.
"""

import pandas as pd

WINDOW_DAYS = 28  # rolling window for the live error
MIN_DAYS = 7  # too few days to call drift before this
DRIFT_MARGIN = 1.0  # alert when the model is this many MAPE points worse than National Gas


def score(forecasts: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """One row per forecast with a trusted actual: errors of the model and of National Gas."""
    actual = daily.loc[daily["demand"].notna(), ["gas_day", "ldz", "demand"]]
    s = forecasts.merge(actual, on=["gas_day", "ldz"], how="inner")
    s["ape_model"] = (s["forecast"] - s["demand"]).abs() / s["demand"] * 100
    s["ape_ng"] = (s["ng_forecast_da"] - s["demand"]).abs() / s["demand"] * 100
    s["in_band"] = s["demand"].between(s["p10"], s["p90"])
    return s.sort_values(["gas_day", "ldz"]).reset_index(drop=True)


def summary(scores: pd.DataFrame, window: int = WINDOW_DAYS) -> dict:
    """Error over the last `window` gas days, model and National Gas scored on the same rows."""
    if scores.empty:
        return {"days": 0}
    recent = scores[scores["gas_day"] > scores["gas_day"].max() - pd.Timedelta(days=window)]
    both = recent.dropna(subset=["ape_ng"])
    return {
        "days": recent["gas_day"].nunique(),
        "first_day": recent["gas_day"].min(),
        "last_day": recent["gas_day"].max(),
        "mape_model": both["ape_model"].mean(),
        "mape_ng": both["ape_ng"].mean(),
        "coverage": recent["in_band"].mean(),
    }


def drift(s: dict, margin: float = DRIFT_MARGIN) -> str | None:
    """A warning message when the live model has fallen behind the benchmark, else None."""
    if s["days"] < MIN_DAYS:
        return None
    if s["mape_model"] > s["mape_ng"] + margin:
        return (
            f"model MAPE {s['mape_model']:.2f}% is more than {margin} points worse than National Gas "
            f"({s['mape_ng']:.2f}%) over the last {s['days']} days: check the inputs, consider retraining"
        )
    return None
