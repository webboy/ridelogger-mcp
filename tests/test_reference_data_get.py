"""reference_data_get filters cached catalog rows for ChatGPT ID lookup."""

from __future__ import annotations

from typing import get_args

from ridelogger_mcp.reference_cache import _rows_from_payload, row_matches_query
from ridelogger_mcp.reference_paths import REFERENCE_PATHS
from ridelogger_mcp.tools.reference import ReferenceDataset


def test_reference_dataset_literal_matches_paths() -> None:
    assert set(get_args(ReferenceDataset)) == set(REFERENCE_PATHS)


def test_rows_from_payload_unwraps_data_envelope() -> None:
    payload = {"data": [{"id": 1, "name": "Claas"}, {"id": 2, "name": "John Deere"}]}
    rows = _rows_from_payload(payload)
    assert [r["name"] for r in rows] == ["Claas", "John Deere"]


def test_row_matches_query_on_name() -> None:
    row = {"id": 10, "name": "Claas"}
    assert row_matches_query(row, "claas")
    assert row_matches_query(row, "CLAA")
    assert not row_matches_query(row, "Fendt")


def test_cache_rows_filters_makes() -> None:
    from ridelogger_mcp.reference_cache import ReferenceCache

    cache = object.__new__(ReferenceCache)
    cache._data = {
        "vehicle_makes": {
            "data": [
                {"id": 1, "name": "Toyota"},
                {"id": 2, "name": "Claas"},
            ]
        }
    }
    rows = [r for r in cache.rows("vehicle_makes") if row_matches_query(r, "Claas")]
    assert rows == [{"id": 2, "name": "Claas"}]


def test_cache_rows_unknown_dataset_raises() -> None:
    from ridelogger_mcp.reference_cache import ReferenceCache

    cache = object.__new__(ReferenceCache)
    cache._data = {}
    try:
        cache.rows("not_a_dataset")
        raise AssertionError("expected KeyError")
    except KeyError as exc:
        assert "Unknown reference dataset" in str(exc)
