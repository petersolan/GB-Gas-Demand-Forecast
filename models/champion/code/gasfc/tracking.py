"""MLflow setup shared by the scripts: a local SQLite tracking store next to the repo."""

import mlflow

from gasfc.config import ROOT

TRACKING_URI = f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}"
MODEL_NAME = "gas-demand-ldz"


def setup(experiment: str) -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(experiment)
