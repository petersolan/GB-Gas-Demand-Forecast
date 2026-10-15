"""Population-weighted weather points per LDZ, then gas-day weather from Open-Meteo.

Writes data/processed/weather_points.parquet and data/processed/ldz_weather.parquet.

    python scripts/03_weather.py
"""

from datetime import date, timedelta

import pandas as pd

from gasfc.config import HISTORY_START, PROCESSED, ROOT
from gasfc.geography import assign_ldz, weather_points
from gasfc.weather import download_points, ldz_weather

POINTS_CSV = ROOT / "reference" / "weather_points.csv"


def main() -> None:
    cells_path = PROCESSED / "population_cells.parquet"
    if cells_path.exists():  # rebuild the points from census population (scripts/02)
        cells = pd.read_parquet(cells_path)
        cells["ldz"] = assign_ldz(cells)
        points = weather_points(cells)
        points.round(6).to_csv(POINTS_CSV, index=False)
    else:  # no census data locally: use the committed points
        points = pd.read_csv(POINTS_CSV)
    points.to_parquet(PROCESSED / "weather_points.parquet", index=False)
    print(f"{len(points)} weather points")

    start = (pd.Timestamp(HISTORY_START) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    end = (date.today() + timedelta(days=1)).isoformat()  # tomorrow: the day being forecast
    download_points(points, start, end)
    weather = ldz_weather(points)
    weather.to_parquet(PROCESSED / "ldz_weather.parquet", index=False)
    share = (weather["weather_source"] == "day_before").mean()
    print(f"wrote ldz_weather: {len(weather):,} rows, {share:.0%} from day-before forecasts")


if __name__ == "__main__":
    main()
