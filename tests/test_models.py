import numpy as np
import pandas as pd

from gasfc.backtest import backtest, scores
from gasfc.models import GBM, CalibratedBand, CWVRegression, SeasonalNaive


def synthetic(days: int = 500, seed: int = 0) -> pd.DataFrame:
    """Two LDZs whose demand falls with temperature until heating switches off."""
    rng = np.random.default_rng(seed)
    rows = []
    for ldz, size in (("WM", 20.0), ("WN", 3.0)):
        t = pd.date_range("2023-01-01", periods=days)
        temp = 10 - 8 * np.cos(2 * np.pi * (t.dayofyear - 20) / 365.25) + rng.normal(0, 2, days)
        demand = size * (0.3 + 0.07 * np.clip(15.5 - temp, 0, None)) * rng.normal(1, 0.02, days)
        rows.append(
            pd.DataFrame(
                {
                    "gas_day": t,
                    "ldz": ldz,
                    "temp_mean": temp,
                    "cwv_forecast_d1": temp,
                    "demand": demand,
                    "dow": t.dayofweek,
                    "is_holiday": 0,
                    "christmas": 0,
                    "ng_forecast_da": demand * 1.03,
                    "weather_source": "day_before",
                }
            )
        )
    df = pd.concat(rows, ignore_index=True)
    df["demand_lag7"] = df.groupby("ldz")["demand"].shift(7)
    df["hdd"] = np.clip(15.5 - df["temp_mean"], 0, None)
    return df


def test_models_beat_a_3pct_biased_benchmark_on_clean_weather_driven_data():
    df = synthetic()
    models = [SeasonalNaive(), CWVRegression(), GBM(["hdd", "temp_mean", "dow"], "gbm")]
    preds = backtest(df, models, "2024-03-01")
    s = scores(preds, [m.name for m in models])
    assert s.loc["cwv_regression", "mape"] < s.loc["ng_forecast_da", "mape"]
    assert s.loc["gbm", "mape"] < s.loc["seasonal_naive", "mape"]


def test_calibrated_band_covers_about_80_percent():
    df = synthetic(days=900)
    band = CalibratedBand(["hdd", "temp_mean", "dow"], cal_days=200).fit(df[df["gas_day"] < "2025-03-01"])
    test = df[df["gas_day"] >= "2025-03-01"]
    p = band.predict(test)
    inside = ((test["demand"] >= p["p10"]) & (test["demand"] <= p["p90"])).mean()
    assert 0.7 <= inside <= 0.95
    assert (p["p10"] <= p["p90"]).all()


def test_backtest_never_trains_on_the_month_it_predicts():
    df = synthetic(days=120)
    seen = []

    class Spy:
        name = "spy"

        def fit(self, train):
            seen.append(train["gas_day"].max())
            return self

        def predict(self, test):
            assert test["gas_day"].min() > seen[-1]
            return np.zeros(len(test))

    backtest(df, [Spy()], "2023-03-01")
    assert len(seen) == 2  # March and April
