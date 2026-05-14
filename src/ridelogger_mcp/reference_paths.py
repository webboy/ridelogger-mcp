"""Public GET endpoints cached by ReferenceCache (relative paths including /api)."""

from __future__ import annotations

REFERENCE_PATHS: dict[str, str] = {
    "countries": "/countries",
    "currencies": "/currencies",
    "vehicle_types": "/vehicle_types",
    "vehicle_makes": "/vehicle_makes",
    "fuel_types": "/fuel_types",
    "fuel_units": "/fuel_units",
    "charge_types": "/charge_types",
    "energy_units": "/energy_units",
    "powertrain_types": "/powertrain_types",
    "service_types": "/service_types",
    "expense_types": "/expense_types",
    "mileage_units": "/mileage_units",
    "steering_sides": "/steering_sides",
    "fuel_consumption_units": "/fuel_consumption_units",
}
