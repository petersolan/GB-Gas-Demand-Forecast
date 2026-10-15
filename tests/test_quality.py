import pandas as pd

from gasfc.quality import choose_target


def frame(d1: list[float], d6: list[float]) -> pd.DataFrame:
    n = len(d1)
    return pd.DataFrame(
        {
            "gas_day": pd.date_range("2024-01-01", periods=n, freq="7D"),  # all Mondays
            "ldz": "WM",
            "cwv_actual": 5.0,
            "demand_d1": d1,
            "demand_d6": d6,
        }
    )


def test_prefers_closed_out_value_when_plausible():
    out = choose_target(frame([20, 20, 21, 19], [20.5, 20, 21, 19]))
    assert out.loc[0, "demand_source"] == "d6"
    assert out.loc[0, "demand"] == 20.5


def test_falls_back_to_first_value_when_closeout_is_broken():
    out = choose_target(frame([20, 20, 21, 19], [0.1, 20, 21, 19]))
    assert out.loc[0, "demand_source"] == "d1"
    assert out.loc[0, "demand"] == 20


def test_flags_sustained_drift_from_operator_forecast():
    n = 120
    df = pd.DataFrame(
        {
            "gas_day": pd.date_range("2024-01-01", periods=n),
            "ldz": "SE",
            "cwv_actual": [5.0] * n,
            "ng_forecast_da": [20.0] * n,
        }
    )
    # days 40-79 read 30% low on both published values: a metering problem, not demand
    df["demand_d1"] = [14.0 if 40 <= i < 80 else 20.0 for i in range(n)]
    df["demand_d6"] = df["demand_d1"]
    out = choose_target(df).set_index("gas_day")
    assert (out["demand_source"].iloc[45:75] == "level_shift").all()
    assert (out["demand_source"].iloc[:25] == "d6").all()


def test_flags_day_when_neither_value_is_plausible():
    out = choose_target(frame([3.7, 20, 21, 19, 20], [3.7, 20, 21, 19, 20]))
    assert out.loc[0, "demand_source"] == "flagged"
    assert pd.isna(out.loc[0, "demand"])
