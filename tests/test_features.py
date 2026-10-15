import pandas as pd

from gasfc.features import build, calendar
from gasfc.weather import gas_day


def test_gas_day_runs_from_five_am():
    t = pd.Series(pd.to_datetime(["2025-01-02 04:59", "2025-01-02 05:00", "2025-01-02 23:00"]))
    assert list(gas_day(t).dt.day) == [1, 2, 2]


def test_holidays_follow_the_ldz_nation():
    # 2 January is a bank holiday in Scotland only; St Andrew's Day 2026 is a Monday holiday in Scotland
    df = pd.DataFrame({"gas_day": pd.to_datetime(["2025-01-02", "2025-01-02"]), "ldz": ["SC", "WM"]})
    assert list(calendar(df)["is_holiday"]) == [1, 0]


def test_lags_only_use_data_available_at_forecast_time():
    days = pd.date_range("2025-01-01", periods=10)
    daily = pd.DataFrame(
        {
            "gas_day": days,
            "ldz": "WM",
            "demand_d1": range(10),
            "demand": [float(i) + 0.5 for i in range(10)],  # closeout differs from first value
            "ng_forecast_da": 1.0,
            "cwv_actual": 5.0,
        }
    )
    weather = pd.DataFrame(
        {
            "gas_day": days,
            "ldz": "WM",
            "temp_mean": 5.0,
            "temp_min": 2.0,
            "temp_max": 8.0,
            "wind_mean": 10.0,
            "solar_mean": 50.0,
        }
    )
    t = build(daily, weather).set_index("gas_day")
    # forecasting 5 Jan at 14:00 on 4 Jan: the latest actual is 3 Jan's first published value
    assert t.loc["2025-01-05", "demand_lag2"] == 2
