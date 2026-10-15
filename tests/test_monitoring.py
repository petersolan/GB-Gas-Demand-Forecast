import pandas as pd

from gasfc.monitoring import drift, score, summary


def forecasts(days: int, model: float, ng: float) -> pd.DataFrame:
    gas_day = pd.date_range("2026-01-01", periods=days)
    return pd.DataFrame(
        {"gas_day": gas_day, "ldz": "WM", "forecast": model, "p10": 9.0, "p90": 11.0, "ng_forecast_da": ng}
    )


def actuals(days: int, demand: float = 10.0) -> pd.DataFrame:
    return pd.DataFrame({"gas_day": pd.date_range("2026-01-01", periods=days), "ldz": "WM", "demand": demand})


def test_scores_only_days_with_a_trusted_actual():
    daily = actuals(5)
    daily.loc[2, "demand"] = None  # flagged by the quality checks
    s = score(forecasts(6, 10.5, 11.0), daily)  # day 6 has no actual yet
    assert len(s) == 4
    assert s["ape_model"].round(6).eq(5.0).all()
    assert s["ape_ng"].round(6).eq(10.0).all()
    assert s["in_band"].all()


def test_summary_uses_the_last_window_of_days():
    s = score(forecasts(40, 10.5, 11.0), actuals(40))
    out = summary(s, window=28)
    assert out["days"] == 28
    assert out["first_day"] == pd.Timestamp("2026-01-13")


def test_drift_flags_a_model_behind_the_benchmark():
    behind = summary(score(forecasts(10, 12.0, 10.5), actuals(10)))  # 20% vs 5%
    ahead = summary(score(forecasts(10, 10.5, 12.0), actuals(10)))
    assert drift(behind) is not None
    assert drift(ahead) is None


def test_no_drift_call_on_too_few_days():
    s = summary(score(forecasts(3, 12.0, 10.5), actuals(3)))
    assert drift(s) is None
