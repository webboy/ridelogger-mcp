# ridelogger-mcp

HTTP [MCP](https://modelcontextprotocol.io/) server ([FastMCP](https://gofastmcp.com/)) — thin wrapper around the **RideLogger API** (`ridelogger-api`). It exposes cached reference data as **resources** and **tools** for auth plus vehicle / log / file CRUD.

**RAG:** Semantic retrieval lives in the internal **`ridelogger-rag`** service and is used from **`ridelogger-ai`** (not from this MCP). This MCP stays the source of **structured** API-backed tools; exact log rows and costs always come from tools here, not from embeddings.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SK_API_URL` | **yes** | API base URL **without** trailing `/api` (e.g. `http://localhost:8082` or `http://sk-api:8082` in Docker). |
| `API_CONSUMER_CODE` | no | Consumer code sent as `X-Api-Consumer` when signing (default `mcp`). |
| `API_CONSUMER_KEY_ID` | no | Public key id from `api-consumers:rotate-key` on the API. If empty (with secret also empty), requests are **not** HMAC-signed (backward compatible). |
| `API_CONSUMER_SECRET` | no | Plain signing secret shown **once** by the API rotate-key command. Never commit this value. |
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

**HMAC (`~/sk/docker/docker-compose.yml`):** `sk-api` runs `php artisan migrate` + `db:seed`, which calls `ApiConsumersBootstrapSeeder` (creates `pwa` / `mcp` consumers and, in `local` + enabled env, a dev key `docker-local`). `sk-mcp` gets matching `API_CONSUMER_KEY_ID` / `API_CONSUMER_SECRET`. On production use `php artisan api-consumers:rotate-key mcp` and set those env vars from the one-time output — do not use the compose dev secret.

---

## MCP server instructions (host prompt)

The FastMCP app sets **`instructions`** on the server (what MCP clients expose as guidance for the model). Current text (see `src/ridelogger_mcp/app.py`):

```
Thin MCP wrapper over the RideLogger REST API (vehicle maintenance logbook). Authenticate with auth_login (email/password) and pass access_token to tools, or send Authorization: Bearer <JWT> on HTTP requests — the server validates it via GET /api/auth/me. Call auth_me to read user settings including preferred currency_id. Expense, fuel, and service logs are multi-currency (each row has currency_id); use reference currencies to convert amounts to one currency before summing — see tool descriptions on those endpoints. Reference data (countries, currencies, …) is available as MCP resources ridelogger://reference/*. Write tools use typed parameters aligned with ridelogger-api FormRequest validation (see each tool's schema in list_tools).
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
| `ridelogger://reference/charge_types` | Charge / charging location types |
| `ridelogger://reference/energy_units` | Energy units (e.g. kWh) |
| `ridelogger://reference/powertrain_types` | Vehicle powertrain (ICE, HEV, PHEV, BEV) |
| `ridelogger://reference/service_types` | Service types |
| `ridelogger://reference/expense_types` | Expense types |
| `ridelogger://reference/mileage_units` | Mileage units |

Manual refresh (no token): tool **`reference_data_refresh`**.

---

## Tool semantics contract (policy resource)

Orchestrators (e.g. **ridelogger-ai**) need machine-readable planner hints. These are **not** embedded in `tools/list` JSON today; they are exposed as one MCP resource:

| URI | MIME | Purpose |
|-----|------|--------|
| **`ridelogger://policy/tool-semantics`** | `application/json` | Per-tool policy: `kind`, `category`, `mutation`, `confirmation` (`none` \| `recommended` \| `required`), `risk`/`risk_level`, `side_effect_scope`, `idempotency`, `requires`, `provides` |

- **Source of truth** in code: [`src/ridelogger_mcp/tool_semantics.py`](src/ridelogger_mcp/tool_semantics.py) (`TOOL_SEMANTICS`, `REGISTERED_TOOL_NAMES`).
- **Envelope** includes `contract_version`, `tools` (name → policy), and `ok`.
- **Rule for new tools**: add the `@mcp.tool` **and** an entry in `REGISTERED_TOOL_NAMES` / `TOOL_SEMANTICS`; `policy_resource_json()` calls `validate_registry()` so drift fails fast.

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
| `vehicles_create` | yes | POST `/api/vehicles` — typed fields (VehicleStoreRequest). |
| `vehicles_get` | yes | GET `/api/vehicles/{id}`. |
| `vehicles_update` | yes | PUT `/api/vehicles/{id}` — **partial** body (VehicleUpdateRequest); only `vehicle_id` required in the tool; omit unused fields. |

**Plate history**

| Tool | Token | Description |
|------|-------|-------------|
| `vehicle_plates_list` | yes | List plates for a vehicle. |
| `vehicle_plates_create` | yes | Create plate — typed fields (VehiclePlateStoreRequest). |
| `vehicle_plates_update` | yes | Update plate — typed fields (VehiclePlateUpdateRequest). |
| `vehicle_plates_delete` | yes | Delete plate. |

**Vehicle images**

| Tool | Token | Description |
|------|-------|-------------|
| `vehicle_images_list` | yes | List images for a vehicle. |
| `vehicle_images_get` | yes | Get image bytes/metadata. |
| `vehicle_images_create` | yes | Upload image — multipart / chat_upload_id per API. |
| `vehicle_images_delete` | yes | Delete image. |

**Fuel logs** (multi-currency — see tool description for `currency_id` / aggregation)

| Tool | Token | Description |
|------|-------|-------------|
| `fuel_logs_list` | yes | GET `.../vehicles/{id}/fuel_logs`. |
| `fuel_logs_create` | yes | POST — typed body (FuelLogStoreRequest + date, …). |
| `fuel_logs_get` | yes | GET one log. |
| `fuel_logs_update` | yes | PUT — optional typed fields (FuelLogUpdateRequest + vehicle log fields). |
| `fuel_logs_delete` | yes | DELETE. |

**Service logs** (multi-currency)

| Tool | Token | Description |
|------|-------|-------------|
| `service_logs_list` | yes | GET `.../vehicles/{id}/service_logs`. |
| `service_logs_create` | yes | POST — typed body (ServiceLogStoreRequest + date, …). |
| `service_logs_get` | yes | GET one log. |
| `service_logs_update` | yes | PUT — optional typed fields. |
| `service_logs_delete` | yes | DELETE. |

**Expense logs** (multi-currency)

| Tool | Token | Description |
|------|-------|-------------|
| `expense_logs_list` | yes | GET `.../vehicles/{id}/expense_logs`. |
| `expense_logs_create` | yes | POST — typed body (ExpenseLogStoreRequest + date, …). |
| `expense_logs_get` | yes | GET one log. |
| `expense_logs_update` | yes | PUT — optional typed fields. |
| `expense_logs_delete` | yes | DELETE. |

**Generic vehicle logs & attachments**

| Tool | Token | Description |
|------|-------|-------------|
| `generic_vehicle_logs_list` | yes | GET `.../vehicles/{id}/vehicle_logs` (aggregated fuel/service/expense). |
| `generic_vehicle_logs_delete` | yes | DELETE a generic vehicle log row. |
| `vehicle_log_files_list` | yes | List files on a vehicle log. |
| `vehicle_log_files_upload` | yes | Multipart upload (file path or base64). Free tier: one attachment per log (403 if full). |
| `vehicle_log_files_upload_base64` | yes | Upload via JSON — `chat_upload_id` or base64 file + name. Same one-file limit for non-premium. |
| `vehicle_log_files_delete` | yes | Delete attachment. |
| `vehicle_log_files_download` | yes | Download attachment bytes. |

Create/update tools expose **explicit parameters**; shapes match **ridelogger-api** FormRequest classes (see `list_tools` → `inputSchema`). Scribe docs on `sk-api` remain the human-readable reference.

---

## Smoke tests

1. **Health**: `curl -s http://localhost:8083/health`
2. **Login** (tool `auth_login` or `curl -X POST http://localhost:8082/api/auth/login -H 'Content-Type: application/json' -d '{"email":"...","password":"..."}'`)
3. **List vehicles** with returned `access_token` via tool `vehicles_list`
4. **Fuel log**: `fuel_logs_create` with amount, currency_id, unit, unit_id, fuel_type_id, mileage, date (and optional fields)
5. **Service logs**: `service_logs_list`
6. **File on vehicle log**: `vehicle_log_files_upload` or `vehicle_log_files_upload_base64` for an existing `vehicle_log_id`

## Design notes

- Only `auth_login` and `reference_data_refresh` omit `access_token`; other tools require a non-empty token and fail fast if missing (unless Bearer is set on the HTTP request).
- Tokens are never logged.
- Upstream errors are mapped to structured `UpstreamApiError` messages (401/403/404/422/429/5xx hints).

## Tool safety semantics (ChatGPT app / MCP clients)

Every tool has explicit FastMCP `annotations` derived from the single source of truth in `tool_semantics.py`:

| Annotation | Rule |
|---|---|
| `readOnlyHint=True` | Tool has `mutation=False` — reads only, no server-side user data changes |
| `destructiveHint=True` | Tool has `risk="high"` — irreversible delete operation |
| `idempotentHint=True` | Tool has `idempotency="idempotent"` — safe to repeat with same arguments |
| `openWorldHint=False` | All tools — operate only on the authenticated user's bounded vehicle data |

**Read tools (22):** `auth_me`, `vehicles_list/get`, `vehicle_plates_list`, `vehicle_images_list/get`, `fuel/charge/service/expense_logs_list/get`, `generic_vehicle_logs_list`, `vehicle_log_files_list/download`, `reminder_slots_list`, `reminder_list/list_user/show`, `reference_data_refresh`

**Destructive delete tools (11, `destructiveHint=True`):** `fuel/charge/service/expense_logs_delete`, `generic_vehicle_logs_delete`, `vehicle_log_files_delete`, `vehicle_images_delete`, `vehicle_plates_delete`, `reminder_delete`

**Write non-destructive (17):** all `_create`, `_update`, `_upload*`, `reminder_complete`, `user_avatar_upload`, `auth_login`, `vehicles_create/update`

### Adding a new tool

1. Add an entry to `TOOL_SEMANTICS` in `tool_semantics.py` (use `_read()` or `_write()` helpers).
2. Add the name to `REGISTERED_TOOL_NAMES`.
3. Add `annotations=get_annotations("tool_name")` to the `@mcp.tool()` decorator.
4. Run `pytest tests/test_tool_annotations.py` — it will fail if step 1 or 2 is missing.
