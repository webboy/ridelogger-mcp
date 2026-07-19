from __future__ import annotations

from ridelogger_mcp.tools.auth import _settings_only
from ridelogger_mcp.tools.common import sanitize_tool_data, tool_success


def test_sanitize_tool_data_removes_personal_and_internal_identifiers() -> None:
    payload = {
        "data": {
            "id": 123,
            "email": "demo@example.com",
            "first_name": "Demo",
            "last_name": "User",
            "username": "demo",
            "phone": "+49123456789",
            "address": "Some Street 1",
            "marketing_consent": True,
            "unsubscribed_at": None,
            "premium": {"valid_to": "2026-10-24"},
            "user_id": 55,
            "uuid": "550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2026-06-30T10:00:00Z",
            "vehicle": {
                "id": 10,
                "name": "Golf",
                "owner_id": 55,
                "service_logs": [
                    {
                        "id": 20,
                        "date": "2026-06-30",
                        "amount": 100,
                        "currency_id": 1,
                        "user_id": 55,
                        "updated_at": "2026-06-30T11:00:00Z",
                    }
                ],
            },
        },
        "pagination": {"page": 1},
    }

    sanitized = sanitize_tool_data(payload)

    assert sanitized == {
        "data": {
            "id": 123,
            "vehicle": {
                "id": 10,
                "name": "Golf",
                "service_logs": [
                    {
                        "id": 20,
                        "date": "2026-06-30",
                        "amount": 100,
                        "currency_id": 1,
                    }
                ],
            },
        },
        "pagination": {"page": 1},
    }


def test_tool_success_sanitizes_data_envelope() -> None:
    assert tool_success({"email": "demo@example.com", "currency_id": 1}) == {
        "ok": True,
        "data": {"currency_id": 1},
    }


def test_sanitize_tool_data_keeps_created_updated_by_out_of_cabinet_documents() -> None:
    payload = {
        "id": 7,
        "title": "Registration",
        "created_by": {"id": 55, "display_name": "Demo User"},
        "updated_by": {"id": 55, "display_name": "Demo User"},
    }
    assert sanitize_tool_data(payload) == {"id": 7, "title": "Registration"}


def test_auth_me_settings_only_allowlist() -> None:
    payload = {
        "data": {
            "id": 9250,
            "display_name": "Demo User",
            "email": "demo@example.com",
            "phone": "+49123456789",
            "address": "Some Street 1",
            "premium": {"valid_to": "2026-10-24"},
            "status": 1,
            "status_id": 1,
            "pivot": {"vehicle_id": 12, "user_id": 9250},
            "country_id": 57,
            "currency_id": 3,
            "language_id": 4,
            "fuel_consumption_unit_id": 1,
            "fuel_consumption_unit": "l/100km",
            "quantity_unit_id": 1,
            "quantity_unit": "l",
            "vehicle_id": 5309,
            "instance": "global",
        }
    }
    assert _settings_only(payload) == {
        "data": {
            "country_id": 57,
            "currency_id": 3,
            "language_id": 4,
            "fuel_consumption_unit_id": 1,
            "fuel_consumption_unit": "l/100km",
            "quantity_unit_id": 1,
            "quantity_unit": "l",
            "vehicle_id": 5309,
            "instance": "global",
        }
    }


def test_sanitize_tool_data_preserves_additive_vehicle_composition_fields() -> None:
    payload = {
        "data": {
            "id": 42,
            "mileage": 12000,
            "vin": "WBAAA11111111111",
            "meters": [
                {
                    "id": 10,
                    "meter_type_id": 1,
                    "current_value": 12000,
                    "is_primary": True,
                }
            ],
            "tanks": [],
            "batteries": [],
            "identifiers": [{"id": 30, "value": "WBAAA11111111111"}],
            "readings": [{"vehicle_meter_id": 10, "value": 12500}],
        }
    }

    sanitized = sanitize_tool_data(payload)

    assert sanitized["data"]["mileage"] == 12000
    assert sanitized["data"]["meters"][0]["current_value"] == 12000
    assert sanitized["data"]["readings"][0]["value"] == 12500


def test_upstream_402_error_message_is_neutral() -> None:
    import httpx

    import pytest

    from ridelogger_mcp.errors import UpstreamApiError, raise_for_status

    resp = httpx.Response(
        402,
        json={"code": 402, "messages": {"general": ["Upgrade to premium to add more."]}},
        request=httpx.Request("POST", "https://api.example.com/api/vehicles"),
    )
    with pytest.raises(UpstreamApiError) as exc_info:
        raise_for_status(resp)

    message = str(exc_info.value).lower()
    assert exc_info.value.status_code == 402
    for term in ("premium", "upgrade", "payment", "subscription"):
        assert term not in message
