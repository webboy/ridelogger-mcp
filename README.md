# ridelogger-mcp

HTTP [MCP](https://modelcontextprotocol.io/) server ([FastMCP](https://gofastmcp.com/)) — thin wrapper around the **RideLogger API** (`ridelogger-api`). It exposes cached reference data as **resources** and **tools** for auth plus vehicle / log / file CRUD.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SK_API_URL` | **yes** | API base URL **without** trailing `/api` (e.g. `http://localhost:8082` or `http://sk-api:8082` in Docker). |
| `REFERENCE_CACHE_TTL_SECONDS` | no | Reference dataset refresh interval (default `3600`). |
| `HTTP_TIMEOUT_S` | no | Upstream HTTP timeout (default `30`). |
| `MCP_HOST` | no | Bind address (default `0.0.0.0`). |
| `MCP_PORT` | no | MCP HTTP port (default `8083`). |
| `LOG_LEVEL` | no | Python log level (default `INFO`). |
| `MCP_VERBOSE_LOGS` | no | Set `true` to log every MCP protocol request (`ListTools`, etc.) and Uvicorn access lines at INFO. Default is **quiet**: those loggers use WARNING because **Cursor polls the server often** while connected. |

### Why do container logs look “busy”?

While Cursor has this MCP enabled, the client **repeatedly** calls `ListTools`, `ListPrompts`, and `ListResources` over `POST /mcp`. That is normal discovery traffic, not a bug. By default we suppress the noisiest lines; set `MCP_VERBOSE_LOGS=true` only when debugging the MCP wire protocol.

## Run locally

```bash
cd ridelogger-mcp
python -m venv .venv && . .venv/bin/activate
pip install -e .
export SK_API_URL=http://localhost:8082
python -m ridelogger_mcp
```

- Health: `GET http://localhost:8083/health`
- MCP (streamable HTTP): `http://localhost:8083/mcp` (see FastMCP client docs)

## Docker (unified stack)

From `~/sk`:

```bash
make mcp-build
make mcp-up
make mcp-logs
```

Service `sk-mcp` uses `SK_API_URL=http://sk-api:8082` and maps port **8083**.

## Resources (cached reference data)

URIs `ridelogger://reference/{name}` for: `countries`, `currencies`, `vehicle_types`, `vehicle_makes`, `fuel_types`, `fuel_units`, `service_types`, `expense_types`, `mileage_units`.

Each payload is JSON: `data`, `fetched_at`, `ttl_seconds`, `source_endpoint`.

Manual refresh: tool `reference_data_refresh` (no token).

## Tools (catalog)

| Tool | Token |
|------|-------|
| `auth_login` | no |
| `auth_me` | yes |
| `reference_data_refresh` | no |
| `vehicles_list`, `vehicles_create`, `vehicles_get`, `vehicles_update` | yes |
| `vehicle_plates_*` (list/create/update/delete) | yes |
| `vehicle_images_*` (list/get/create/delete) | yes |
| `fuel_logs_*`, `service_logs_*`, `expense_logs_*` (list/create/get/update/delete) | yes |
| `generic_vehicle_logs_list`, `generic_vehicle_logs_delete` | yes |
| `vehicle_log_files_*` (list/upload/upload_base64/delete/download) | yes |

Create/update tools expect **`body_json`** as a JSON **object string** matching the Laravel API request bodies (see `http://localhost:8082/docs` when `sk-api` is running).

## Smoke tests

1. **Health**: `curl -s http://localhost:8083/health`
2. **Login** (tool `auth_login` or `curl -X POST http://localhost:8082/api/auth/login -H 'Content-Type: application/json' -d '{"email":"...","password":"..."}'`)
3. **List vehicles** with returned `access_token` via tool `vehicles_list`
4. **Fuel log**: `fuel_logs_create` with `body_json` for amount, currency_id, unit, unit_id, fuel_type_id, mileage, date
5. **Service logs**: `service_logs_list`
6. **File on vehicle log**: `vehicle_log_files_upload` or `vehicle_log_files_upload_base64` for an existing `vehicle_log_id`

## Design notes

- Only `auth_login` omits `access_token`; all other tools require a non-empty token and fail fast if missing.
- Tokens are never logged.
- Upstream errors are mapped to structured `UpstreamApiError` messages (401/403/404/422/429/5xx hints).
