import pandas as pd
import pytest

from gasfc.geography import assign_ldz


def cells(rows: list[tuple[str, str | None, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["ctry26cd", "rgn26cd", "lad26cd"])


@pytest.mark.parametrize(
    ("ctry", "rgn", "lad", "ldz"),
    [
        ("E92000001", "E12000005", "E08000025", "WM"),  # Birmingham: whole region
        ("E92000001", "E12000007", "E09000033", "NT"),  # Westminster: north of the Thames
        ("E92000001", "E12000007", "E09000028", "SE"),  # Southwark: south of the Thames
        ("E92000001", "E12000008", "E07000110", "SE"),  # Maidstone, Kent
        ("E92000001", "E12000008", "E06000045", "SO"),  # Southampton
        ("E92000001", "E12000009", "E06000058", "SO"),  # Bournemouth, Christchurch & Poole
        ("E92000001", "E12000002", "E06000063", "NO"),  # Cumberland
        ("W92000004", None, "W06000005", "WN"),  # Flintshire
        ("W92000004", None, "W06000015", "WS"),  # Cardiff
        ("S92000003", None, "S12000049", "SC"),  # Glasgow
    ],
)
def test_assign_ldz(ctry, rgn, lad, ldz):
    assert assign_ldz(cells([(ctry, rgn, lad)])).iloc[0] == ldz


def test_unknown_area_fails_loudly():
    with pytest.raises(ValueError):
        assign_ldz(cells([("N92000002", None, "N09000003")]))  # Northern Ireland: no GB LDZ
