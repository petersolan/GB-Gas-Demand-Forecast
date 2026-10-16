import pandas as pd

from gasfc.nationalgas import as_of_cutoff, day_ahead_forecast


def versions(issued: list[str], values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "gas_day": pd.Timestamp("2026-01-10"),
            "ldz": "WM",
            "value": values,
            "applicable_at": pd.to_datetime(issued),
        }
    )


def test_uses_the_version_published_by_14_00_on_the_day_before():
    # the CWV forecast is reissued at 08:00, 12:00, 15:00 and 23:00 on the day before
    fc = versions(
        ["2026-01-09 08:00", "2026-01-09 12:00", "2026-01-09 15:00", "2026-01-09 23:00"],
        [1.72, 1.81, 1.85, 1.90],
    )
    assert as_of_cutoff(fc, "cwv").loc[:, "cwv"].tolist() == [1.81]


def test_day_ahead_demand_forecast_of_zero_is_missing():
    fc = versions(["2026-01-09 09:00", "2026-01-09 13:00"], [20.0, 0.0])
    assert day_ahead_forecast(fc)["ng_forecast_da"].isna().all()
