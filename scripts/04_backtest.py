"""Rolling-origin backtest of all candidate models against National Gas's day-ahead forecast.

Retrains every model monthly from the test start and logs each one to MLflow (scores, per-LDZ errors).
Writes data/processed/backtest_predictions.parquet for the dashboard.

    python scripts/04_backtest.py --start 2024-10-01
"""

import argparse
import tempfile
from pathlib import Path

import mlflow
import pandas as pd

from gasfc.backtest import backtest, interval_coverage, scores, scores_by_ldz, skill
from gasfc.config import PROCESSED
from gasfc.features import build
from gasfc.models import CalibratedBand, candidates
from gasfc.serving import FEATURES
from gasfc.tracking import setup


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--start", default="2024-10-01", help="first month forecast (day-before weather from Feb 2024)"
    )
    a = ap.parse_args()

    daily = pd.read_parquet(PROCESSED / "ldz_daily.parquet")
    weather = pd.read_parquet(PROCESSED / "ldz_weather.parquet")
    table = build(daily, weather)

    models = candidates()
    models += [CalibratedBand(FEATURES)]  # writes band_p10 and band_p90
    preds = backtest(table, models, a.start)
    preds.to_parquet(PROCESSED / "backtest_predictions.parquet", index=False)

    point = [m.name for m in models if m.name != "band"]
    table_scores = scores(preds, point)
    table_scores["skill_vs_ng_pct"] = skill(table_scores)
    by_ldz = scores_by_ldz(preds, point)
    coverage = interval_coverage(preds, "band_p10", "band_p90")
    print(table_scores.to_string())
    print(f"\np10-p90 interval coverage: {coverage:.1%} (target 80%)")
    print("\nMAPE % by LDZ:\n" + by_ldz.to_string())

    setup("gas-demand-backtest")
    for model in models:
        if model.name not in table_scores.index:
            continue
        with mlflow.start_run(run_name=model.name):
            mlflow.log_params(
                {
                    "model": model.name,
                    "test_start": a.start,
                    "retrain": "monthly",
                    "features": ",".join(getattr(model, "features", []))[:500],
                }
            )
            mlflow.log_metrics(table_scores.loc[model.name].drop("days").to_dict())
            if model.name == "gbm_ng_correction":
                mlflow.log_metric("p10_p90_coverage", coverage)  # quantile models share its features
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "mape_by_ldz.csv"
                by_ldz[[model.name]].to_csv(path)
                mlflow.log_artifact(str(path))
    with mlflow.start_run(run_name="ng_forecast_da (benchmark)"):
        mlflow.log_param("model", "national_gas_day_ahead")
        mlflow.log_metrics(table_scores.loc["ng_forecast_da"].drop("days").to_dict())


if __name__ == "__main__":
    main()
