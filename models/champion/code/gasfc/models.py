"""Forecasting models, from a naive baseline to gradient boosting.

All models share one interface: fit(train) then predict(test), on the feature table from
gasfc.features. Training rows without a trusted demand value (flagged days) are dropped.
"""

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from gasfc.features import CALENDAR, CWV, LAGS, OPERATOR, POP_WEATHER


class SeasonalNaive:
    """Demand one week earlier: the simplest forecast that respects the weekly cycle."""

    name = "seasonal_naive"

    def fit(self, train: pd.DataFrame) -> "SeasonalNaive":
        return self

    def predict(self, test: pd.DataFrame) -> np.ndarray:
        return test["demand_lag7"].to_numpy()


class CWVRegression:
    """Per-LDZ linear regression on the CWV with a heating hinge, weekday and holidays.

    Mirrors the traditional approach: demand falls with the composite weather variable until heating
    switches off, then flattens. The hinge at the CWV where that happens is fitted per LDZ by grid search.
    """

    name = "cwv_regression"

    def _design(self, df: pd.DataFrame, hinge: float) -> np.ndarray:
        cwv = df["cwv_forecast_d1"].to_numpy()
        days = pd.get_dummies(df["dow"].astype(int)).reindex(columns=range(7), fill_value=0).to_numpy()[:, 1:]
        return np.column_stack([cwv, np.maximum(cwv - hinge, 0), days, df["is_holiday"], df["christmas"]])

    def fit(self, train: pd.DataFrame) -> "CWVRegression":
        self.models = {}
        for ldz, g in train.dropna(subset=["demand", "cwv_forecast_d1"]).groupby("ldz"):
            best = None
            for hinge in np.arange(10, 19, 0.5):
                m = LinearRegression().fit(self._design(g, hinge), g["demand"])
                sse = ((m.predict(self._design(g, hinge)) - g["demand"]) ** 2).sum()
                if best is None or sse < best[0]:
                    best = (sse, hinge, m)
            self.models[ldz] = best[1:]
        return self

    def predict(self, test: pd.DataFrame) -> np.ndarray:
        out = np.full(len(test), np.nan)
        for ldz, idx in test.groupby("ldz").indices.items():
            hinge, m = self.models[ldz]
            out[idx] = m.predict(self._design(test.iloc[idx], hinge))
        return out


class GBM:
    """One LightGBM model across all LDZs, predicting demand relative to the LDZ's typical level.

    Scaling by each LDZ's mean demand lets zones of very different size share what they learn about
    weather and calendar effects. `features` selects the weather inputs, so the value of the
    population-weighted weather can be measured by leaving it out.
    """

    SCALED = ("demand_lag2", "demand_lag7", "demand_mean_2_8", "ng_forecast_da")

    def __init__(
        self,
        features: list[str],
        name: str,
        quantile: float | None = None,
        half_life_days: float | None = 365,
        seed: int = 0,
    ):
        self.features = features + ["ldz_code"]
        self.name = name
        # recent years count more: demand levels drift (prices, efficiency), weather response less so
        self.half_life_days = half_life_days
        params = {
            "n_estimators": 600,
            "learning_rate": 0.03,
            "num_leaves": 31,
            "min_child_samples": 20,
            "subsample": 0.8,
            "subsample_freq": 1,
            "colsample_bytree": 0.8,
            "random_state": seed,
            "verbose": -1,
        }
        if quantile is not None:
            params |= {"objective": "quantile", "alpha": quantile}
        self.model = lgb.LGBMRegressor(**params)

    def _x(self, df: pd.DataFrame) -> pd.DataFrame:
        x = df.copy()
        x["ldz_code"] = x["ldz"].astype("category").cat.set_categories(self.ldzs)
        for col in self.SCALED:
            if col in self.features:
                x[col] = x[col] / x["ldz"].map(self.scale)
        return x[self.features]

    def fit(self, train: pd.DataFrame) -> "GBM":
        train = train.dropna(subset=["demand"])
        self.ldzs = sorted(train["ldz"].unique())
        self.scale = train.groupby("ldz")["demand"].mean()
        y = train["demand"] / train["ldz"].map(self.scale)
        weight = None
        if self.half_life_days:
            age = (train["gas_day"].max() - train["gas_day"]).dt.days
            weight = 0.5 ** (age / self.half_life_days)
        self.model.fit(self._x(train), y, sample_weight=weight)
        return self

    def predict(self, test: pd.DataFrame) -> np.ndarray:
        return self.model.predict(self._x(test)) * test["ldz"].map(self.scale).to_numpy()


class CalibratedBand:
    """P10-P90 range from quantile LightGBM, widened by conformal calibration to really cover 80%.

    Quantile models trained on the past tend to be overconfident on the future. The pair is first fitted
    without the last `cal_days`; on those held-out days, the conformity score is how far the actual fell
    outside the range, relative to the range's centre. The score's coverage quantile becomes a
    multiplicative widening, applied after refitting on all the data. A full year of calibration covers
    both winter and summer.
    """

    name = "band"

    def __init__(self, features: list[str], coverage: float = 0.8, cal_days: int = 365, seed: int = 0):
        self.features, self.coverage, self.cal_days, self.seed = features, coverage, cal_days, seed

    def _pair(self) -> tuple[GBM, GBM]:
        lo_q, hi_q = (1 - self.coverage) / 2, (1 + self.coverage) / 2
        return (
            GBM(self.features, "lo", quantile=lo_q, seed=self.seed),
            GBM(self.features, "hi", quantile=hi_q, seed=self.seed),
        )

    def fit(self, train: pd.DataFrame) -> "CalibratedBand":
        train = train.dropna(subset=["demand"])
        cut = train["gas_day"].max() - pd.Timedelta(days=self.cal_days)
        fit_part, cal = train[train["gas_day"] <= cut], train[train["gas_day"] > cut]
        lo, hi = self._pair()
        lo.fit(fit_part), hi.fit(fit_part)
        a, b = lo.predict(cal), hi.predict(cal)
        low, high = np.minimum(a, b), np.maximum(a, b)
        mid = (low + high) / 2
        y = cal["demand"].to_numpy()
        score = np.maximum((low - y) / mid, (y - high) / mid)
        n = len(score)
        level = min(1.0, np.ceil((n + 1) * self.coverage) / n)
        self.widen = max(0.0, float(np.quantile(score, level)))
        self.lo, self.hi = self._pair()
        self.lo.fit(train), self.hi.fit(train)
        return self

    def predict(self, test: pd.DataFrame) -> dict[str, np.ndarray]:
        a, b = self.lo.predict(test), self.hi.predict(test)
        low, high = np.minimum(a, b), np.maximum(a, b)
        mid = (low + high) / 2
        return {"p10": low - self.widen * mid, "p90": high + self.widen * mid}


def candidates() -> list:
    """The models compared in the backtest.

    The first five forecast demand from scratch; the last also sees National Gas's own day-ahead
    forecast (published before the gas day) and learns to correct its systematic errors.
    """
    base = LAGS + CALENDAR
    return [
        SeasonalNaive(),
        CWVRegression(),
        GBM(base + CWV, "gbm_cwv"),
        GBM(base + POP_WEATHER, "gbm_pop_weather"),
        GBM(base + CWV + POP_WEATHER, "gbm_cwv_pop_weather"),
        GBM(base + CWV + POP_WEATHER + OPERATOR, "gbm_ng_correction"),
    ]
