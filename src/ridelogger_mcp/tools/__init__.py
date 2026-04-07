"""Register all MCP tools."""

from __future__ import annotations

from fastmcp import FastMCP

from ridelogger_mcp.tools import (
    auth,
    charge_logs,
    expense_logs,
    fuel_logs,
    images,
    plates,
    reference,
    reminders,
    service_logs,
    vehicle_logs,
    vehicles,
)


def register_all(mcp: FastMCP) -> None:
    auth.register(mcp)
    vehicles.register(mcp)
    plates.register(mcp)
    images.register(mcp)
    fuel_logs.register(mcp)
    charge_logs.register(mcp)
    service_logs.register(mcp)
    expense_logs.register(mcp)
    vehicle_logs.register(mcp)
    reference.register(mcp)
    reminders.register(mcp)
