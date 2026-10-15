"""Train the forecaster on all trusted history and register it in MLflow as the new champion.

The registered model is a pyfunc (point forecast + P10 / P90), so the daily job and any serving layer
load it by alias without knowing how it was built:

    python scripts/05_train_register.py
"""

import mlflow
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature

from gasfc.config import PROCESSED
from gasfc.features import build
from gasfc.serving import FEATURES, DemandForecaster
from gasfc.tracking import MODEL_NAME, setup


def main() -> None:
    daily = pd.read_parquet(PROCESSED / "ldz_daily.parquet")
    weather = pd.read_parquet(PROCESSED / "ldz_weather.parquet")
    table = build(daily, weather)
    train = table.dropna(subset=["demand"])
    model = DemandForecaster().fit(train)

    sample = table.dropna(subset=["demand"]).tail(50)
    columns = ["ldz", "gas_day", *FEATURES]
    signature = infer_signature(sample[columns], model.predict(None, sample[columns]))

    setup("gas-demand-training")
    with mlflow.start_run(run_name="train_champion") as run:
        mlflow.log_params(
            {
                "features": ",".join(FEATURES),
                "rows": len(train),
                "first_day": str(train["gas_day"].min().date()),
                "last_day": str(train["gas_day"].max().date()),
            }
        )
        info = mlflow.pyfunc.log_model(
            name="model",
            python_model=model,
            signature=signature,
            input_example=sample[columns].head(3),
            code_paths=["src/gasfc"],
            registered_model_name=MODEL_NAME,
        )
        client = MlflowClient()
        version = info.registered_model_version
        client.set_registered_model_alias(MODEL_NAME, "champion", version)
        print(f"registered {MODEL_NAME} v{version} as champion (run {run.info.run_id})")


if __name__ == "__main__":
    main()
