"""A deployable forecaster: the point model plus a calibrated P10-P90 range, packaged for MLflow."""

import mlflow.pyfunc
import pandas as pd

from gasfc.features import CALENDAR, CWV, LAGS, OPERATOR, POP_WEATHER
from gasfc.models import GBM, CalibratedBand

FEATURES = LAGS + CALENDAR + CWV + POP_WEATHER + OPERATOR


class DemandForecaster(mlflow.pyfunc.PythonModel):
    """predict(feature table) -> ldz, gas_day, forecast, p10, p90 (mcm/day)."""

    def __init__(self, seed: int = 0):
        self.point = GBM(FEATURES, "point", seed=seed)
        self.band = CalibratedBand(FEATURES, seed=seed)

    def fit(self, table: pd.DataFrame) -> "DemandForecaster":
        self.point.fit(table)
        self.band.fit(table)
        return self

    def predict(self, context, model_input: pd.DataFrame, params=None) -> pd.DataFrame:
        out = model_input[["ldz", "gas_day"]].copy()
        out["forecast"] = self.point.predict(model_input)
        band = self.band.predict(model_input)
        out["p10"], out["p90"] = band["p10"], band["p90"]
        return out
