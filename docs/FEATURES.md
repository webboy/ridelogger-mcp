# ridelogger-mcp — Features & Tool Catalog

**Last verified:** 2026-07-04

> Ecosystem-level documentation: `~/sk/memory/docs/`.

This document enumerates everything the MCP server exposes: **56 tools**, **15 MCP resources**, custom HTTP endpoints, and client-integration features. Source of truth in code: `src/ridelogger_mcp/tool_semantics.py` (`REGISTERED_TOOL_NAMES`, `TOOL_SEMANTICS`) and `src/ridelogger_mcp/tools/*.py`; the pytest suite `tests/test_tool_annotations.py` fails if they drift.

## Classification legend

Derived from `TOOL_SEMANTICS` and the FastMCP annotations built from it:

| Class | Meaning |
|---|---|
| **Read** | `mutation=False`, `readOnlyHint=True`, idempotent — retrieves data only |
| **Write** | `mutation=True`, additive create/upload — `destructiveHint=False` |
| **Write (destructive)** | `mutation=True` and `destructiveHint=True` — deletes, overwrites, or irreversibly advances user data. Deletes additionally carry `risk=high` / `confirmation=required`; updates/overwrites carry `confirmation=recommended` |

All tools have `openWorldHint=False` (bounded user data). All tools except `reference_data_refresh` require OAuth/Bearer authorization (token validated upstream via `GET /api/auth/me`). `reminder_slots_list` serves public reference data upstream but the tool itself still requires a token.

## Tool catalog (56 tools)

### Auth (1)

| Tool | Purpose | Class |
|---|---|---|
| `auth_me` | Current account settings only (GET `/api/auth/me`, reduced to a settings allowlist), incl. preferred `currency_id` for multi-currency aggregation. No profile identity fields (name/email/phone/address/tier) are returned | Read |

No username/password login tools are exposed — authentication happens via the MCP client's OAuth/Bearer flow.

### User (1)

| Tool | Purpose | Class |
|---|---|---|
| `user_avatar_upload` | Upload/replace profile avatar (POST `/api/user/avatar`) via ChatGPT `avatar`, `chat_upload_id`, or base64 | Write (destructive — replaces existing avatar) |

### Vehicles (4)

| Tool | Purpose | Class |
|---|---|---|
| `vehicles_list` | List vehicles the user can manage (GET `/api/vehicles`) | Read |
| `vehicles_get` | Get one vehicle by id (GET `/api/vehicles/{id}`) | Read |
| `vehicles_create` | Create a vehicle (POST `/api/vehicles`), typed fields per `VehicleStoreRequest` | Write |
| `vehicles_update` | Partial update (PUT `/api/vehicles/{id}`); only changed fields sent | Write (destructive — overwrites fields) |

### Plate history (4)

| Tool | Purpose | Class |
|---|---|---|
| `vehicle_plates_list` | List plates for a vehicle (GET `.../vehicle_plates`) | Read |
| `vehicle_plates_create` | Create plate record (POST), per `VehiclePlateStoreRequest` | Write |
| `vehicle_plates_update` | Update plate (PUT `.../vehicle_plates/{plate_id}`) | Write (destructive) |
| `vehicle_plates_delete` | Delete plate (DELETE) | Write (destructive, confirmation required) |

### Vehicle images / gallery (4)

| Tool | Purpose | Class |
|---|---|---|
| `vehicle_images_list` | List gallery images (GET `.../images`) | Read |
| `vehicle_images_get` | Download one image as base64 + content type (GET `.../images/{image_id}`) | Read |
| `vehicle_images_create` | Upload image via ChatGPT `image`, `chat_upload_id`, or base64 (POST `.../images`) | Write |
| `vehicle_images_delete` | Delete image (DELETE `.../images/{image_id}`) | Write (destructive, confirmation required) |

### Vehicle cabinet — private documents (6)

| Tool | Purpose | Class |
|---|---|---|
| `vehicle_cabinet_list` | List cabinet documents (GET `.../cabinet-documents`) | Read |
| `vehicle_cabinet_get` | Get one document's metadata (GET `.../cabinet-documents/{document_id}`) | Read |
| `vehicle_cabinet_download` | Download document bytes (GET `.../cabinet-documents/{document_id}/download`) | Read |
| `vehicle_cabinet_create` | Upload a cabinet document (POST `.../cabinet-documents`) via ChatGPT `cabinet_file`, `chat_upload_id`, or base64 | Write |
| `vehicle_cabinet_update` | Update document metadata/file (PUT) via optional ChatGPT `cabinet_file` or base64; metadata-only OK | Write (destructive) |
| `vehicle_cabinet_delete` | Delete document (DELETE) | Write (destructive, confirmation required) |

### Fuel logs (5) — multi-currency

| Tool | Purpose | Class |
|---|---|---|
| `fuel_logs_list` | List fuel logs with date/currency/type filters (GET `.../fuel_logs`) | Read |
| `fuel_logs_get` | Get one fuel log (GET `.../fuel_logs/{fuel_log_id}`) | Read |
| `fuel_logs_create` | Create fuel log (POST), per `FuelLogStoreRequest` + date | Write |
| `fuel_logs_update` | Update fuel log (PUT) | Write (destructive) |
| `fuel_logs_delete` | Delete fuel log (DELETE) | Write (destructive, confirmation required) |

### Charge logs (5) — multi-currency, EV charging

| Tool | Purpose | Class |
|---|---|---|
| `charge_logs_list` | List charge logs with date/currency/charge-type filters (GET `.../charge_logs`) | Read |
| `charge_logs_get` | Get one charge log (GET `.../charge_logs/{charge_log_id}`) | Read |
| `charge_logs_create` | Create charge log (POST) — amount, currency, mileage, date, energy required | Write |
| `charge_logs_update` | Update charge log (PUT) | Write (destructive) |
| `charge_logs_delete` | Delete charge log (DELETE) | Write (destructive, confirmation required) |

### Service logs (5) — multi-currency

| Tool | Purpose | Class |
|---|---|---|
| `service_logs_list` | List service logs with filters (GET `.../service_logs`) | Read |
| `service_logs_get` | Get one service log (GET `.../service_logs/{service_log_id}`) | Read |
| `service_logs_create` | Create service log (POST) incl. optional geolocation + rating | Write |
| `service_logs_update` | Update service log (PUT) | Write (destructive) |
| `service_logs_delete` | Delete service log (DELETE) | Write (destructive, confirmation required) |

### Expense logs (5) — multi-currency

| Tool | Purpose | Class |
|---|---|---|
| `expense_logs_list` | List expense logs with filters (GET `.../expense_logs`) | Read |
| `expense_logs_get` | Get one expense log (GET `.../expense_logs/{expense_log_id}`) | Read |
| `expense_logs_create` | Create expense log (POST) | Write |
| `expense_logs_update` | Update expense log (PUT) | Write (destructive) |
| `expense_logs_delete` | Delete expense log (DELETE) | Write (destructive, confirmation required) |

### Generic vehicle logs (2)

| Tool | Purpose | Class |
|---|---|---|
| `generic_vehicle_logs_list` | List all log entries for a vehicle across types (GET `.../vehicle_logs`) with date/currency filters | Read |
| `generic_vehicle_logs_delete` | Delete a generic vehicle log row (DELETE `.../vehicle_logs/{vehicle_log_id}`) | Write (destructive, confirmation required) |

### Vehicle log file attachments (5)

| Tool | Purpose | Class |
|---|---|---|
| `vehicle_log_files_list` | List attachments on a vehicle log (GET `.../get_files`) | Read |
| `vehicle_log_files_download` | Download attachment bytes as base64 (GET `.../download_files/{uuid}`) | Read |
| `vehicle_log_files_upload` | Multipart upload via ChatGPT `vehicle_log_file`, `chat_upload_id`, or base64 (POST `.../put_files`); 402 when attachment limit reached | Write |
| `vehicle_log_files_upload_base64` | JSON-body upload variant (POST `.../put_files_cordova`); no OpenAI file param | Write |
| `vehicle_log_files_delete` | Delete one attachment by media uuid (DELETE `.../delete_files/{uuid}`) | Write (destructive, confirmation required) |

### Reminders (8)

| Tool | Purpose | Class |
|---|---|---|
| `reminder_slots_list` | List built-in reminder slots (GET `/api/reminder_slots`) — public reference data (tool still requires a token) | Read |
| `reminder_list` | List reminders for a vehicle, optional status filter (GET `.../reminders`) | Read |
| `reminder_list_user` | List reminders for the user across all vehicles (GET `/api/user/reminders`) | Read |
| `reminder_show` | Get one reminder (GET `.../reminders/{reminder_id}`) | Read |
| `reminder_create` | Create reminder (POST `.../reminders`); prefers built-in slots (technical inspection, oil change, tire swaps, brake check) | Write |
| `reminder_update` | Update custom reminder name/description (PUT) | Write (destructive) |
| `reminder_delete` | Delete reminder (DELETE) | Write (destructive, confirmation required) |
| `reminder_complete` | Mark complete; recurring reminders spawn the next occurrence (POST `.../complete`) | Write (destructive — irreversibly advances state) |

### Reference (1)

| Tool | Purpose | Class |
|---|---|---|
| `reference_data_refresh` | Reload all cached reference datasets from the API (no token) | Described as `[WRITE]` with `readOnlyHint=False` — it mutates the MCP server's cache (never user records); internal semantics stay `mutation=False` |

## MCP resources (15)

### Reference data — `ridelogger://reference/{name}` (14)

All `application/json`; envelope `{data, fetched_at, ttl_seconds, source_endpoint}`; refreshed at startup and every `REFERENCE_CACHE_TTL_SECONDS` (default 3600 s), or on demand via `reference_data_refresh`.

| URI | Dataset |
|---|---|
| `ridelogger://reference/countries` | Countries |
| `ridelogger://reference/currencies` | Currencies (codes, exchange values — needed for multi-currency aggregation) |
| `ridelogger://reference/vehicle_types` | Vehicle types |
| `ridelogger://reference/vehicle_makes` | Vehicle makes |
| `ridelogger://reference/fuel_types` | Fuel types |
| `ridelogger://reference/fuel_units` | Fuel units |
| `ridelogger://reference/charge_types` | Charge / charging location types |
| `ridelogger://reference/energy_units` | Energy units (e.g. kWh) |
| `ridelogger://reference/powertrain_types` | Powertrains (ICE, HEV, PHEV, BEV) |
| `ridelogger://reference/service_types` | Service types |
| `ridelogger://reference/expense_types` | Expense types |
| `ridelogger://reference/mileage_units` | Mileage units |
| `ridelogger://reference/steering_sides` | Steering side (LHD/RHD) |
| `ridelogger://reference/fuel_consumption_units` | Consumption display units (l/100km, MPG variants) |

### Tool policy — `ridelogger://policy/tool-semantics` (1)

`application/json`. Machine-readable per-tool policy consumed by the **ridelogger-ai** orchestrator: `kind`, `category`, `mutation`, `confirmation` (`none|recommended|required`), `risk`/`risk_level`, `side_effect_scope`, `idempotency`, `requires`, `provides`. Envelope includes `contract_version` (currently `2026-04-23.1`) and `ok`. See `docs/ARCHITECTURE.md` → "Tool semantics policy".

## MCP prompts

**None.** The server registers no FastMCP prompts; only the server-level `instructions` string applies.

## HTTP endpoints (non-MCP)

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness + config diagnostics: `ok`, `service`, `version`, `api_upstream`, `api_consumer` (code, key-id hint, HMAC configured flags). No secrets. |
| `GET /.well-known/oauth-protected-resource` (also `/mcp`-suffixed/prefixed variants) | OAuth protected-resource metadata: resource URL, authorization server, supported scopes, `bearer_methods_supported: ["header"]` |
| `GET /.well-known/openai-apps-challenge` | OpenAI Apps domain-verification token (plain text); 404 when `OPENAI_APPS_CHALLENGE_TOKEN` unset |
| `POST /mcp` | MCP streamable HTTP transport |

## Client integration features

### OAuth flow (ChatGPT App / external MCP clients)

- MCP **discovery is public** (`initialize`, `tools/list`, `resources/list`) so OpenAI Platform and other clients can scan the server without credentials.
- Clients discover the authorization server from the protected-resource metadata (`OAUTH_AUTHORIZATION_SERVER`, default `https://api.ridelogger.com`) and run the OAuth flow against ridelogger-api.
- Supported scopes: `profile:read`, `vehicles:read`, `vehicles:write`, `logs:read`, `logs:write`, `files:read`, `files:write`, `reminders:read`.
- The obtained token is sent as `Authorization: Bearer` on MCP HTTP requests; the server validates it per tool call against `GET /api/auth/me` (`RideLoggerBearerMiddleware`).
- ChatGPT App submission metadata lives in `chatgpt-app-submission.json` at the repo root.

### OpenAI Platform scanner compatibility

- `Content-Type: application/octet-stream` on `POST /mcp` is normalized to `application/json`; `Accept` is widened to include both `application/json` and `text/event-stream`.
- Empty-body `POST /mcp` probes receive `204 No Content`.
- Domain verification via the challenge route above.

### Safety annotations (ChatGPT Apps / MCP clients)

Every tool carries explicit FastMCP `ToolAnnotations` derived from `tool_semantics.py`: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint=False`. The invariant is enforced by `tests/test_tool_annotations.py` — a new tool without a `TOOL_SEMANTICS` entry cannot ship.

### Response hygiene

Tool responses are passed through `sanitize_tool_data()`, which strips personal and internal fields (emails, names, tokens, session/device ids, sync UUIDs, internal timestamps) while keeping domain fields and the record ids needed for follow-up calls.
