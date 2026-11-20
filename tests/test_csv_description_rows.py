"""Every shared game-config CSV must keep a description row as row 2.

`src.utils.df.load_csv` always treats row 2 as a human-readable description
row and starts reading data from row 3. A CSV that omits the description row
silently loses its first record, so guard the convention here.
"""

import csv
from pathlib import Path

import pytest

from src.utils.df import load_csv

CONFIG_DIR = Path(__file__).resolve().parents[1] / "static" / "game_configs"
CSV_PATHS = sorted(CONFIG_DIR.glob("*.csv"))


def _rows(path: Path) -> list[list[str]]:
    with open(path, "r", encoding="utf-8-sig") as handle:
        return [row for row in csv.reader(handle) if row]


@pytest.mark.parametrize("path", CSV_PATHS, ids=lambda p: p.name)
def test_row_two_is_a_description_row(path: Path):
    rows = _rows(path)
    data_ids = [row[0].strip() for row in rows[2:]]
    if len(rows) < 3 or not all(value.isdigit() for value in data_ids):
        pytest.skip(f"{path.name} does not use integer ids")
    assert not rows[1][0].strip().isdigit(), (
        f"{path.name} row 2 looks like data; add a description row so the first record is not dropped"
    )


@pytest.mark.parametrize("name", ["material", "fortune", "misfortune", "random_minor_event"])
def test_previously_dropped_first_records_are_loaded(name: str):
    records = load_csv(CONFIG_DIR / f"{name}.csv")
    assert records[0]["id"] == 1
