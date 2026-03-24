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

- Health: `GET http://localhost:8083/health` → JSON includes `ok`, `service`, and **`version`** (package version).
- MCP (streamable HTTP): `http://localhost:8083/mcp` (see FastMCP client docs)

## Docker (unified stack)

From `~/sk`:

```bash
make mcp-build
make mcp-up
make mcp-logs
```

Service `sk-mcp` uses `SK_API_URL=http://sk-api:8082` and maps port **8083**.

---

## MCP server instructions (host prompt)

The FastMCP app sets **`instructions`** on the server (what MCP clients expose as guidance for the model). Current text (see `src/ridelogger_mcp/app.py`):

```
Thin MCP wrapper over RideLogger (Servisna knjižica) REST API. Authenticate with auth_login (email/password) and pass access_token to tools, or send Authorization: Bearer <JWT> on HTTP requests — the server validates it via GET /api/auth/me. Call auth_me to read user settings including preferred currency_id. Expense, fuel, and service logs are multi-currency (each row has currency_id); use reference currencies to convert amounts to one currency before summing — see tool descriptions on those endpoints. Reference data (countries, currencies, …) is available as MCP resources ridelogger://reference/*. Use body_json parameters as JSON object strings matching the API request bodies.
```

---

## MCP prompts

**None.** This project does not register FastMCP `prompt` handlers. `ListPrompts` from clients will not return custom prompts; only the server **`instructions`** above apply.

---

## MCP resources (cached reference data)

Each resource is **`application/json`**. URI pattern: **`ridelogger://reference/{name}`**.

Payload envelope: `data`, `fetched_at`, `ttl_seconds`, `source_endpoint`.

| URI | Dataset |
|-----|---------|
| `ridelogger://reference/countries` | Countries |
| `ridelogger://reference/currencies` | Currencies (codes, rates — use with multi-currency logs) |
| `ridelogger://reference/vehicle_types` | Vehicle types |
| `ridelogger://reference/vehicle_makes` | Vehicle makes |
| `ridelogger://reference/fuel_types` | Fuel types |
| `ridelogger://reference/fuel_units` | Fuel units |
| `ridelogger://reference/service_types` | Service types |
| `ridelogger://reference/expense_types` | Expense types |
| `ridelogger://reference/mileage_units` | Mileage units |

Manual refresh (no token): tool **`reference_data_refresh`**.

---

## MCP tools (full catalog)

**Auth:** `access_token` = optional if the HTTP client sends `Authorization: Bearer <JWT>` (middleware validates via `/api/auth/me`).

| Tool | Token | Description |
|------|-------|-------------|
| `auth_login` | no | POST `/api/auth/login` — email, password; returns `access_token` / refresh. |
| `auth_me` | yes | GET `/api/auth/me` — profile and `currency_id` (display currency). |
| `reference_data_refresh` | no | Reload all cached reference datasets from the API. |

**Vehicles**

| Tool | Token | Description |
|------|-------|-------------|
| `vehicles_list` | yes | GET `/api/vehicles` (optional `page`). |
| `vehicles_create` | yes | POST `/api/vehicles` — `body_json`. |
| `vehicles_get` | yes | GET `/api/vehicles/{id}`. |
| `vehicles_update` | yes | PUT `/api/vehicles/{id}` — `body_json`. |

**Plate history**

| Tool | Token | Description |
|------|-------|-------------|
| `vehicle_plates_list` | yes | List plates for a vehicle. |
| `vehicle_plates_create` | yes | Create plate — `body_json`. |
| `vehicle_plates_update` | yes | Update plate — `body_json`. |
| `vehicle_plates_delete` | yes | Delete plate. |

**Vehicle images**

| Tool | Token | Description |
|------|-------|-------------|
| `vehicle_images_list` | yes | List images for a vehicle. |
| `vehicle_images_get` | yes | Get image bytes/metadata. |
| `vehicle_images_create` | yes | Upload image — `body_json` / multipart per API. |
| `vehicle_images_delete` | yes | Delete image. |

**Fuel logs** (multi-currency — see tool description for `currency_id` / aggregation)

| Tool | Token | Description |
|------|-------|-------------|
| `fuel_logs_list` | yes | GET `.../vehicles/{id}/fuel_logs`. |
| `fuel_logs_create` | yes | POST — `body_json`. |
| `fuel_logs_get` | yes | GET one log. |
| `fuel_logs_update` | yes | PUT — `body_json`. |
| `fuel_logs_delete` | yes | DELETE. |

**Service logs** (multi-currency)

| Tool | Token | Description |
|------|-------|-------------|
| `service_logs_list` | yes | GET `.../vehicles/{id}/service_logs`. |
| `service_logs_create` | yes | POST — `body_json`. |
| `service_logs_get` | yes | GET one log. |
| `service_logs_update` | yes | PUT — `body_json`. |
| `service_logs_delete` | yes | DELETE. |

**Expense logs** (multi-currency)

| Tool | Token | Description |
|------|-------|-------------|
| `expense_logs_list` | yes | GET `.../vehicles/{id}/expense_logs`. |
| `expense_logs_create` | yes | POST — `body_json`. |
| `expense_logs_get` | yes | GET one log. |
| `expense_logs_update` | yes | PUT — `body_json`. |
| `expense_logs_delete` | yes | DELETE. |

**Generic vehicle logs & attachments**

| Tool | Token | Description |
|------|-------|-------------|
| `generic_vehicle_logs_list` | yes | GET `.../vehicles/{id}/vehicle_logs` (aggregated fuel/service/expense). |
| `generic_vehicle_logs_delete` | yes | DELETE a generic vehicle log row. |
| `vehicle_log_files_list` | yes | List files on a vehicle log. |
| `vehicle_log_files_upload` | yes | Multipart upload (file path or base64). |
| `vehicle_log_files_upload_base64` | yes | Upload via base64 payload. |
| `vehicle_log_files_delete` | yes | Delete attachment. |
| `vehicle_log_files_download` | yes | Download attachment bytes. |

Create/update tools that take **`body_json`** expect a JSON **object string** matching the Laravel API bodies (see Scribe docs when `sk-api` is running).

---

## Smoke tests

1. **Health**: `curl -s http://localhost:8083/health`
2. **Login** (tool `auth_login` or `curl -X POST http://localhost:8082/api/auth/login -H 'Content-Type: application/json' -d '{"email":"...","password":"..."}'`)
3. **List vehicles** with returned `access_token` via tool `vehicles_list`
4. **Fuel log**: `fuel_logs_create` with `body_json` for amount, currency_id, unit, unit_id, fuel_type_id, mileage, date
5. **Service logs**: `service_logs_list`
6. **File on vehicle log**: `vehicle_log_files_upload` or `vehicle_log_files_upload_base64` for an existing `vehicle_log_id`

## Design notes

- Only `auth_login` and `reference_data_refresh` omit `access_token`; other tools require a non-empty token and fail fast if missing (unless Bearer is set on the HTTP request).
- Tokens are never logged.
- Upstream errors are mapped to structured `UpstreamApiError` messages (401/403/404/422/429/5xx hints).
