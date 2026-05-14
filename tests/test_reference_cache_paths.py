"""Smoke checks for reference cache endpoints."""

from __future__ import annotations

import unittest

from ridelogger_mcp.reference_paths import REFERENCE_PATHS


class ReferencePathsRegionalMeasurementTest(unittest.TestCase):
    def test_steering_sides_and_consumption_units_registered(self) -> None:
        self.assertEqual(REFERENCE_PATHS["steering_sides"], "/steering_sides")
        self.assertEqual(REFERENCE_PATHS["fuel_consumption_units"], "/fuel_consumption_units")


if __name__ == "__main__":
    unittest.main()
