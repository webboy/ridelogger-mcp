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
Thin MCP wrapper over the RideLogger REST API (vehicle maintenance logbook). Authenticate through the MCP client's OAuth/Bearer flow and send Authorization: Bearer on HTTP requests — the server validates it via GET /api/auth/me. Expense, fuel, and service logs are multi-currency (each row has currency_id); use reference currencies to convert amounts to one currency before summing — see tool descriptions on those endpoints. Reference data (countries, currencies, …) is available as MCP resources ridelogger://reference/*. Write tools use typed parameters aligned with ridelogger-api FormRequest validation (see each tool's schema in list_tools).
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
| `ridelogger://reference/vehicle_types` | Vehicle types (includes agri ids **4–7**: tractor, combine, trailer_attachment, work_machine) |
| `ridelogger://reference/vehicle_makes` | Vehicle makes |
| `ridelogger://reference/fuel_types` | Fuel types |
| `ridelogger://reference/fuel_units` | Fuel units |
| `ridelogger://reference/charge_types` | Charge / charging location types |
| `ridelogger://reference/energy_units` | Energy units (e.g. kWh) |
| `ridelogger://reference/powertrain_types` | Vehicle powertrain (ICE, HEV, PHEV, BEV) |
| `ridelogger://reference/service_types` | Service types |
| `ridelogger://reference/expense_types` | Expense types |
| `ridelogger://reference/mileage_units` | Mileage units (1=km, 2=mile, **3=hour** for agri engine hours) |
| `ridelogger://reference/steering_sides` | Steering side (LHD/RHD) |
| `ridelogger://reference/fuel_consumption_units` | Fuel consumption display units (l/100km, MPG variants) |

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

**56 tools.** Full catalog with read/write/destructive classification: **[`docs/FEATURES.md`](docs/FEATURES.md)**. Architecture details: **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**.

**Auth:** MCP discovery requests (`initialize`, `tools/list`, `resources/list`) are public so ChatGPT/OpenAI Platform and other clients can scan the server. User-data tool calls require OAuth/Bearer and should send `Authorization: Bearer <token>` on MCP HTTP requests. The tool-call middleware validates the token via `/api/auth/me`. No username/password auth tools are exposed.

### ChatGPT-native file attachments

Five upload tools declare OpenAI Apps SDK file parameters via `_meta["openai/fileParams"]`:

| Tool | File argument | Upstream multipart field |
|------|---------------|--------------------------|
| `user_avatar_upload` | `avatar` | `avatar` |
| `vehicle_images_create` | `image` | `image` |
| `vehicle_cabinet_create` | `cabinet_file` | `cabinet_file` |
| `vehicle_cabinet_update` | `cabinet_file` (optional replacement) | `cabinet_file` |
| `vehicle_log_files_upload` | `vehicle_log_file` | `vehicle_log_file` |

When the user attaches a file in ChatGPT, the host injects a top-level object `{download_url, file_id, mime_type?, file_name?}`. MCP downloads the temporary HTTPS URL inside the tool call (bounded streaming, SSRF checks, MIME validation) and forwards bytes to the existing RideLogger API multipart endpoints.

**Three distinct file sources** (mutually exclusive on create/upload tools):

1. **ChatGPT attachment** — OpenAI `file_id` + `download_url` on the file-reference argument above.
2. **RideLogger `chat_upload_id`** — internal UUID from `ai_chat_uploaded_files` (AI/PWA pipeline); **not** an OpenAI file id.
3. **Base64 fallback** — `file_base64` + `file_name` for other MCP clients (`vehicle_log_files_upload_base64` remains JSON-only and has no OpenAI file param).

Implementation: `src/ridelogger_mcp/file_inputs.py`.

| Tool | Token | Description |
|------|-------|-------------|
| `auth_me` | yes | GET `/api/auth/me` — account settings only (settings allowlist incl. `currency_id` display currency; no profile identity fields). No username/password login tool is exposed. |
| `reference_data_refresh` | no | Reload all cached reference datasets from the API. |

**User profile**

| Tool | Token | Description |
|------|-------|-------------|
| `user_avatar_upload` | yes | POST `/api/user/avatar` — upload/replace profile avatar (ChatGPT `avatar`, `chat_upload_id`, or base64). |

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
| `vehicle_images_create` | yes | Upload image — ChatGPT `image`, `chat_upload_id`, or base64. |
| `vehicle_images_delete` | yes | Delete image. |

**Vehicle cabinet (private documents)**

| Tool | Token | Description |
|------|-------|-------------|
| `vehicle_cabinet_list` | yes | GET `.../vehicles/{id}/cabinet-documents`. |
| `vehicle_cabinet_get` | yes | Get one document's metadata. |
| `vehicle_cabinet_download` | yes | Download document bytes. |
| `vehicle_cabinet_create` | yes | Upload a cabinet document (ChatGPT `cabinet_file`, `chat_upload_id`, or base64). |
| `vehicle_cabinet_update` | yes | Update metadata and/or replace file (ChatGPT `cabinet_file` or base64; metadata-only OK). |
| `vehicle_cabinet_delete` | yes | Delete document. |

**Fuel logs** (multi-currency — see tool description for `currency_id` / aggregation)

| Tool | Token | Description |
|------|-------|-------------|
| `fuel_logs_list` | yes | GET `.../vehicles/{id}/fuel_logs`. |
| `fuel_logs_create` | yes | POST — typed body (FuelLogStoreRequest + date, …). |
| `fuel_logs_get` | yes | GET one log. |
| `fuel_logs_update` | yes | PUT — optional typed fields (FuelLogUpdateRequest + vehicle log fields). |
| `fuel_logs_delete` | yes | DELETE. |

**Charge logs** (multi-currency, EV charging)

| Tool | Token | Description |
|------|-------|-------------|
| `charge_logs_list` | yes | GET `.../vehicles/{id}/charge_logs`. |
| `charge_logs_create` | yes | POST — typed body (ChargeLogStoreRequest: amount, currency_id, mileage, date, energy). |
| `charge_logs_get` | yes | GET one log. |
| `charge_logs_update` | yes | PUT — optional typed fields. |
| `charge_logs_delete` | yes | DELETE. |

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
| `vehicle_log_files_upload` | yes | Multipart upload via ChatGPT `vehicle_log_file`, `chat_upload_id`, or base64. The API may return 402 when the log attachment limit is reached. |
| `vehicle_log_files_upload_base64` | yes | JSON upload via `chat_upload_id` or base64 (no ChatGPT file param). The API may return 402 when the attachment limit is reached. |
| `vehicle_log_files_delete` | yes | Delete attachment. |
| `vehicle_log_files_download` | yes | Download attachment bytes. |

**Reminders**

| Tool | Token | Description |
|------|-------|-------------|
| `reminder_slots_list` | yes | GET `/api/reminder_slots` — built-in slots (public reference data, but the tool still requires authorization). |
| `reminder_list` | yes | GET `.../vehicles/{id}/reminders` — optional status filter (active/passed/canceled/completed). |
| `reminder_list_user` | yes | GET `/api/user/reminders` — reminders across all vehicles. |
| `reminder_show` | yes | GET one reminder. |
| `reminder_create` | yes | POST — prefer built-in slots (inspection, oil, tire swaps, brakes) via `reminder_slot_id`. |
| `reminder_update` | yes | PUT — custom reminder name/description only. |
| `reminder_delete` | yes | DELETE. |
| `reminder_complete` | yes | POST `.../complete` — mark complete; recurring creates next occurrence. |

Create/update tools expose **explicit parameters**; shapes match **ridelogger-api** FormRequest classes (see `list_tools` → `inputSchema`). Scribe docs on `sk-api` remain the human-readable reference.

---

## Unit tests (pytest)

Install dev deps and run the suite from repo root:

```bash
cd ridelogger-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

- **Annotation / registry parity:** `tests/test_tool_annotations.py` — `REGISTERED_TOOL_NAMES`, `TOOL_SEMANTICS`, FastMCP `list_tools`, and annotation hints stay aligned when tools change.
- **Tool dispatch stubs:** `tests/test_tool_dispatch_upstream.py` exercises every registered tool name against a stubbed RideLogger HTTP client.

## Smoke tests

1. **Health**: `curl -s http://localhost:8083/health`
2. **Authenticate** the MCP HTTP client with OAuth/Bearer.
3. **List vehicles** with `Authorization: Bearer <token>` via tool `vehicles_list`
4. **Fuel log**: `fuel_logs_create` with amount, currency_id, unit, fuel_type_id, mileage, date (optional `unit_id`; optional fields)
5. **Service logs**: `service_logs_list`
6. **File on vehicle log**: `vehicle_log_files_upload` or `vehicle_log_files_upload_base64` for an existing `vehicle_log_id`

## Design notes

- User-data tools require OAuth/Bearer authorization on the MCP HTTP request (`Authorization: Bearer …`, validated via middleware). Token injection uses FastMCP `Depends(ToolToken)` — no legacy `access_token` tool argument.
- The HTTP app accepts OpenAI Platform scan requests that send JSON-RPC with broad `Accept` headers and `Content-Type: application/octet-stream` by normalizing those headers for `POST /mcp` only.
- Empty `POST /mcp` scanner probes receive `204 No Content`; non-empty JSON-RPC discovery requests can list tools publicly for scanner compatibility.
- Tokens are never logged.
- Upstream errors are mapped to structured `UpstreamApiError` messages (401/403/404/422/429/5xx hints).

## Tool safety semantics (ChatGPT app / MCP clients)

Every tool has explicit FastMCP `annotations` derived from the single source of truth in `tool_semantics.py`:

| Annotation | Rule |
|---|---|
| `readOnlyHint=True` | Tool only retrieves or computes data and does not change RideLogger or MCP server state |
| `destructiveHint=True` | Tool can delete, overwrite, replace, or irreversibly advance user data |
| `idempotentHint=True` | Tool has `idempotency="idempotent"` — safe to repeat with same arguments |
| `openWorldHint=False` | All tools — operate only on the authenticated user's bounded vehicle data |

**Read-only tools:** `auth_me`, `vehicles_list/get`, `vehicle_plates_list`, `vehicle_images_list/get`, `vehicle_cabinet_list/get/download`, `fuel/charge/service/expense_logs_list/get`, `generic_vehicle_logs_list`, `vehicle_log_files_list/download`, `reminder_slots_list`, `reminder_list/list_user/show`

**State-changing non-user-data tool:** `reference_data_refresh` refreshes the MCP server's reference cache, so `readOnlyHint=False` even though it does not mutate the user's RideLogger records.

**Destructive tools (`destructiveHint=True`):** delete tools (`fuel/charge/service/expense_logs_delete`, `generic_vehicle_logs_delete`, `vehicle_log_files_delete`, `vehicle_images_delete`, `vehicle_cabinet_delete`, `vehicle_plates_delete`, `reminder_delete`) plus overwrite/replace/status tools (`user_avatar_upload`, `vehicles_update`, `vehicle_plates_update`, `vehicle_cabinet_update`, `fuel/charge/service/expense_logs_update`, `reminder_update`, `reminder_complete`).

**Write non-destructive:** additive create/upload tools such as `vehicles_create`, `vehicle_plates_create`, `vehicle_images_create`, `vehicle_cabinet_create`, `fuel/charge/service/expense_logs_create`, `vehicle_log_files_upload*`, and `reminder_create`.

### Adding a new tool

1. Add an entry to `TOOL_SEMANTICS` in `tool_semantics.py` (use `_read()` or `_write()` helpers).
2. Add the name to `REGISTERED_TOOL_NAMES`.
3. Add `annotations=get_annotations("tool_name")` to the `@mcp.tool()` decorator.
4. Run `pytest tests/test_tool_annotations.py` — it will fail if step 1 or 2 is missing.

## CI

Changes merge to `main` via pull request only. The required GitHub Actions check is **`ci`** (see `.github/workflows/ci.yml`).
