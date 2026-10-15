"""MLflow setup shared by the scripts: a local SQLite tracking store next to the repo."""

import shutil

import mlflow

from gasfc.config import CHAMPION_DIR, ROOT

TRACKING_URI = f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}"
MODEL_NAME = "gas-demand-ldz"


def setup(experiment: str) -> None:
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(experiment)


def export_champion() -> None:
    """Copy the registry's champion to models/champion, the folder the daily job deploys from.

    The registry lives in a local SQLite file that is not committed; the exported folder is a complete
    MLflow model (pickled pyfunc, code, pinned requirements) that loads with no registry at all.
    """
    setup("gas-demand-training")
    shutil.rmtree(CHAMPION_DIR, ignore_errors=True)
    CHAMPION_DIR.parent.mkdir(exist_ok=True)
    mlflow.artifacts.download_artifacts(f"models:/{MODEL_NAME}@champion", dst_path=str(CHAMPION_DIR))
