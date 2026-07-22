from pathlib import Path

import pandas as pd
import pytest

from src.storage.raw_data_storage import RawDataStorage


@pytest.fixture
def storage(tmp_path: Path) -> RawDataStorage:
    return RawDataStorage(tmp_path / "raw")


def test_save_and_load_json_preserves_data(storage: RawDataStorage) -> None:
    data = {"data": [{"Code": "72030", "CoName": "トヨタ自動車"}]}

    saved_path = storage.save_json("jquants", "companies", data, "companies")

    assert saved_path == storage.base_dir / "jquants" / "companies" / "companies.json"
    assert storage.load_json(saved_path) == data
    assert "トヨタ自動車" in saved_path.read_text(encoding="utf-8")


def test_load_json_accepts_path_relative_to_base(storage: RawDataStorage) -> None:
    storage.save_json("jquants", "prices", [{"C": 100}], "72030")

    loaded = storage.load_json("jquants/prices/72030.json")

    assert loaded == [{"C": 100}]


def test_save_csv_preserves_columns_and_rows(storage: RawDataStorage) -> None:
    dataframe = pd.DataFrame([{"Code": "72030", "CoName": "トヨタ自動車"}])

    saved_path = storage.save_csv("jquants", "companies", dataframe, "companies")
    loaded = pd.read_csv(saved_path, dtype=str)

    assert saved_path.suffix == ".csv"
    assert loaded.to_dict(orient="records") == [
        {"Code": "72030", "CoName": "トヨタ自動車"}
    ]


@pytest.mark.parametrize(
    ("source", "category", "file_name"),
    [
        ("../outside", "companies", "data"),
        ("jquants", "../outside", "data"),
        ("jquants", "companies", "../data"),
        ("jquants", "companies", ""),
    ],
)
def test_save_rejects_unsafe_paths(
    storage: RawDataStorage,
    source: str,
    category: str,
    file_name: str,
) -> None:
    with pytest.raises(ValueError, match="safe path segment"):
        storage.save_json(source, category, {}, file_name)


def test_load_rejects_path_outside_base_dir(
    storage: RawDataStorage,
    tmp_path: Path,
) -> None:
    outside_path = tmp_path / "outside.json"
    outside_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the raw data directory"):
        storage.load_json(outside_path)
