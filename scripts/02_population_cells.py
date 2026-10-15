"""Sum census population at address points into 5 km cells per local authority.

Input is the GB-Census-Population-Map output: Census 2021/2022 population disaggregated to 41.6M
UPRN address points (ONSUD locations). 41M points become a few thousand cells, each with the
population-weighted centre of its people, which is all the weather weighting needs.

    python scripts/02_population_cells.py --census-dir ../Census-distribution/data/processed
"""

import argparse
from pathlib import Path

import duckdb

from gasfc.config import PROCESSED, ROOT

CELL_M = 5000


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--census-dir", type=Path, default=ROOT.parent / "Census-distribution" / "data" / "processed"
    )
    a = ap.parse_args()
    onsud = (a.census_dir / "onsud_uprn.parquet").as_posix()
    people = (a.census_dir / "uprn_population.parquet").as_posix()
    con = duckdb.connect()
    cells = con.execute(
        f"""
        WITH p AS (
            SELECT o.ctry26cd, o.rgn26cd, o.lad26cd,
                   o.geometry.x AS x, o.geometry.y AS y,
                   u.population AS pop
            FROM '{onsud}' o JOIN '{people}' u USING (uprn)
            WHERE u.population > 0
        )
        SELECT ctry26cd, rgn26cd, lad26cd,
               floor(x / {CELL_M})::INT AS cell_x, floor(y / {CELL_M})::INT AS cell_y,
               sum(pop) AS population,
               sum(pop * x) / sum(pop) AS easting, sum(pop * y) / sum(pop) AS northing
        FROM p
        GROUP BY ALL
        """
    ).df()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "population_cells.parquet"
    cells.to_parquet(out, index=False)
    print(f"wrote {out}: {len(cells):,} cells, {int(cells['population'].sum()):,} people")


if __name__ == "__main__":
    main()
