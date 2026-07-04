from __future__ import annotations

from ridelogger_mcp.tools.common import sanitize_tool_data, tool_success


def test_sanitize_tool_data_removes_personal_and_internal_identifiers() -> None:
    payload = {
        "data": {
            "id": 123,
            "email": "demo@example.com",
            "first_name": "Demo",
            "last_name": "User",
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
