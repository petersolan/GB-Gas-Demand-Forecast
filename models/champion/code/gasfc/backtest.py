"""Rolling-origin backtest: retrain each month on everything before it, forecast that month.

This mimics production: a model only ever sees the past. Scores are computed on days with a trusted
actual (flagged days excluded for every model alike), next to National Gas's own day-ahead forecast.
"""

import numpy as np
import pandas as pd

WINTER = (11, 12, 1, 2, 3)


def backtest(table: pd.DataFrame, models: list, start: str) -> pd.DataFrame:
    """Predictions for every model, LDZ and gas day from `start`, retrained monthly."""
    months = pd.date_range(pd.Timestamp(start), table["gas_day"].max(), freq="MS")
    rows = []
    for m in months:
        train = table[table["gas_day"] < m]
        test = table[(table["gas_day"] >= m) & (table["gas_day"] < m + pd.offsets.MonthBegin(1))]
        if test.empty:
            continue
        out = test[["gas_day", "ldz", "demand", "ng_forecast_da", "weather_source"]].copy()
        for model in models:
            pred = model.fit(train).predict(test)
            if isinstance(pred, dict):  # range models return several columns (p10, p90)
                for col, values in pred.items():
                    out[f"{model.name}_{col}"] = values
            else:
                out[model.name] = pred
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def scores(preds: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    """MAPE (%) and MAE (mcm/day) per model, overall and for winter / summer months."""
    p = preds.dropna(subset=["demand", "ng_forecast_da"])
    p = p.dropna(subset=models)  # same rows for every model
    winter = p["gas_day"].dt.month.isin(WINTER)
    out = {}
    for m in ["ng_forecast_da", *models]:
        err = p[m] - p["demand"]
        ape = err.abs() / p["demand"] * 100
        out[m] = {
            "mape": ape.mean(),
            "mape_winter": ape[winter].mean(),
            "mape_summer": ape[~winter].mean(),
            "mae": err.abs().mean(),
            "bias": err.mean(),
            "days": len(p),
        }
    return pd.DataFrame(out).T.round(3)


def scores_by_ldz(preds: pd.DataFrame, models: list[str]) -> pd.DataFrame:
    p = preds.dropna(subset=["demand", "ng_forecast_da", *models])
    res = {
        m: (p[m] - p["demand"]).abs().div(p["demand"]).mul(100).groupby(p["ldz"]).mean()
        for m in ["ng_forecast_da", *models]
    }
    return pd.DataFrame(res).round(2)


def skill(scores_table: pd.DataFrame, reference: str = "ng_forecast_da") -> pd.Series:
    """Percentage MAPE improvement over the reference (positive = better)."""
    return (1 - scores_table["mape"] / scores_table.loc[reference, "mape"]).mul(100).round(1)


def interval_coverage(preds: pd.DataFrame, low: str, high: str) -> float:
    p = preds.dropna(subset=["demand", low, high])
    return float(np.mean((p["demand"] >= p[low]) & (p["demand"] <= p[high])))
