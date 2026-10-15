"""Archive National Gas LDZ demand, forecasts and CWVs, then build data/processed/ldz_daily.parquet.

python scripts/01_download_nationalgas.py
"""

from datetime import date

from gasfc.config import HISTORY_START, PROCESSED, SERIES
from gasfc.nationalgas import build_daily, download


def main() -> None:
    today = date.today()
    for series in SERIES:
        print(f"downloading {series}")
        download(series, HISTORY_START, today)
    daily = build_daily()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "ldz_daily.parquet"
    daily.to_parquet(out, index=False)
    first, last = daily["gas_day"].min(), daily["gas_day"].max()
    print(f"wrote {out}: {len(daily):,} rows, {first:%Y-%m-%d} to {last:%Y-%m-%d}")


if __name__ == "__main__":
    main()
