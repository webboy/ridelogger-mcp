"""Unit tests for log list query param helpers (no HTTP)."""

from __future__ import annotations

import unittest

from ridelogger_mcp.tools.common import compact_query_params


class CompactQueryParamsTest(unittest.TestCase):
    def test_returns_none_when_all_none(self) -> None:
        self.assertIsNone(
            compact_query_params(
                {
                    "page": None,
                    "from": None,
                    "to": None,
                    "currency_id": None,
                    "fuel_type_id": None,
                }
            )
        )

    def test_maps_inclusive_date_keys_for_api(self) -> None:
        d = compact_query_params(
            {
                "page": 2,
                "from": "2026-01-01",
                "to": "2026-12-31",
                "currency_id": 1,
                "fuel_type_id": 3,
            }
        )
        self.assertEqual(
            d,
            {
                "page": 2,
                "from": "2026-01-01",
                "to": "2026-12-31",
                "currency_id": 1,
                "fuel_type_id": 3,
            },
        )

    def test_drops_none_only(self) -> None:
        d = compact_query_params({"page": None, "from": "2024-06-01", "currency_id": None})
        self.assertEqual(d, {"from": "2024-06-01"})


if __name__ == "__main__":
    unittest.main()
