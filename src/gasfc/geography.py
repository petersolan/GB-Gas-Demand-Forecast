"""Approximate LDZ geography from local authorities, and population-weighted weather points per LDZ.

LDZ boundaries are not published as open data, but LDZs largely follow regional and county borders.
Each local authority district (LAD) is assigned to one LDZ: whole regions where an LDZ matches a
region, with county-level splits where it does not (London north / south of the Thames, Kent, Surrey
and East Sussex in SE, Dorset in SO, Cumbria in NO, north Wales in WN). This is an approximation; it
only steers where weather is sampled, and the weights come from where people actually live.
"""

import numpy as np
import pandas as pd
from pyproj import Transformer
from sklearn.cluster import KMeans

SCOTLAND, WALES = "S92000003", "W92000004"
REGION_LDZ = {
    "E12000001": "NO",  # North East
    "E12000002": "NW",  # North West
    "E12000003": "NE",  # Yorkshire and The Humber
    "E12000004": "EM",  # East Midlands
    "E12000005": "WM",  # West Midlands
    "E12000006": "EA",  # East of England
    "E12000007": "NT",  # London (south of the Thames overridden below)
    "E12000008": "SO",  # South East (Kent, Surrey, East Sussex overridden below)
    "E12000009": "SW",  # South West (Dorset overridden below)
}


def _codes(prefix: str, first: int, last: int) -> set[str]:
    return {f"{prefix}{i:06d}" for i in range(first, last + 1)}


LAD_LDZ = {
    # Cumbria: Cumberland, Westmorland and Furness
    **dict.fromkeys(["E06000063", "E06000064"], "NO"),
    # London boroughs south of the Thames
    **dict.fromkeys(
        [
            "E09000004",
            "E09000006",
            "E09000008",
            "E09000011",
            "E09000021",
            "E09000022",
            "E09000023",
            "E09000024",
            "E09000027",
            "E09000028",
            "E09000029",
            "E09000032",
        ],
        "SE",
    ),
    # Kent and Medway, East Sussex and Brighton & Hove, Surrey
    **dict.fromkeys(_codes("E07", 105, 116) | {"E06000035"}, "SE"),
    **dict.fromkeys(_codes("E07", 61, 65) | {"E06000043"}, "SE"),
    **dict.fromkeys(_codes("E07", 207, 217), "SE"),
    # Dorset and Bournemouth, Christchurch & Poole
    **dict.fromkeys(["E06000058", "E06000059"], "SO"),
    # North Wales: Anglesey, Gwynedd, Conwy, Denbighshire, Flintshire, Wrexham, and Powys
    **dict.fromkeys(_codes("W06", 1, 6) | {"W06000023"}, "WN"),
}


def assign_ldz(cells: pd.DataFrame) -> pd.Series:
    """LDZ for each population cell, from its local authority, region and country codes."""
    ldz = cells["lad26cd"].map(LAD_LDZ)
    ldz = ldz.fillna(cells["rgn26cd"].map(REGION_LDZ))
    ldz = ldz.mask(ldz.isna() & (cells["ctry26cd"] == SCOTLAND), "SC")
    ldz = ldz.mask(ldz.isna() & (cells["ctry26cd"] == WALES), "WS")
    if ldz.isna().any():
        raise ValueError(f"{int(ldz.isna().sum())} cells have no LDZ")
    return ldz


def weather_points(cells: pd.DataFrame, per_ldz: int = 3, seed: int = 0) -> pd.DataFrame:
    """Population-weighted k-means centres per LDZ, each weighted by its share of the LDZ's people.

    Returns ldz, point, easting, northing, latitude, longitude, weight (weights sum to 1 per LDZ).
    """
    to_wgs84 = Transformer.from_crs(27700, 4326, always_xy=True)
    rows = []
    for ldz, g in cells.groupby("ldz"):
        xy = g[["easting", "northing"]].to_numpy()
        km = KMeans(n_clusters=per_ldz, n_init=10, random_state=seed)
        labels = km.fit_predict(xy, sample_weight=g["population"].to_numpy())
        for k in range(per_ldz):
            m = labels == k
            w = g["population"].to_numpy()[m]
            x, y = np.average(xy[m, 0], weights=w), np.average(xy[m, 1], weights=w)
            lon, lat = to_wgs84.transform(x, y)
            rows.append((ldz, k, x, y, lat, lon, w.sum()))
    pts = pd.DataFrame(rows, columns=["ldz", "point", "easting", "northing", "latitude", "longitude", "pop"])
    pts["weight"] = pts["pop"] / pts.groupby("ldz")["pop"].transform("sum")
    return pts.drop(columns="pop").sort_values(["ldz", "point"]).reset_index(drop=True)
