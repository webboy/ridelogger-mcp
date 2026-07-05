# ridelogger-mcp — Architecture

**Last verified:** 2026-07-04

> Ecosystem-level documentation: `~/sk/memory/docs/`.

`ridelogger-mcp` is an HTTP [MCP](https://modelcontextprotocol.io/) server built on **FastMCP 2** (Python 3.11+, version **1.2.0**). It is a *thin, typed wrapper* over the RideLogger REST API (`ridelogger-api`): every tool maps to one upstream endpoint, no business logic lives here. It exposes **56 tools**, **15 resources** (14 reference datasets + 1 policy resource), and a handful of custom HTTP routes (health, OAuth metadata, OpenAI Apps challenge).

## High-level flow

```
MCP client (Cursor / ChatGPT / ridelogger-ai)
        │  streamable HTTP  POST /mcp  (Authorization: Bearer <JWT>)
        ▼
FastMCP app (app.py)
  ├─ ASGI middleware: McpOctetStreamJsonMiddleware (OpenAI scanner compat)
  ├─ MCP middleware: RideLoggerBearerMiddleware (validates Bearer on tool calls)
  ├─ 56 tools (tools/*.py)  ──►  ApiClient (httpx, HMAC-signed)  ──►  ridelogger-api
  └─ 15 resources (resources.py) ──► ReferenceCache (in-memory, TTL refresh)
```

## Entry point

| Step | Code |
|---|---|
| `python -m ridelogger_mcp` (or console script `ridelogger-mcp`) | `src/ridelogger_mcp/__main__.py` → `main()` |
| `main()` calls | `app.run_server()` |
| `run_server()` | builds `Settings`, sets up logging, then `mcp.run(transport="http", host, port, middleware=http_middleware())` — default bind `0.0.0.0:8083` |

The `FastMCP` instance (`mcp`) is created at module import time in `app.py` with the server name `"RideLogger MCP"`, a lifespan function, and server-level `instructions` (auth guidance, multi-currency warning, reference resource pointers). Tools and resources are registered at import time via `register_all(mcp)` and `register_resources(mcp)`.

## App composition (`src/ridelogger_mcp/app.py`)

### Lifespan (`lifespan_fn`)

On startup:

1. Instantiate `Settings` (pydantic-settings, reads `.env` / environment).
2. `setup_logging(...)` — structured logs with per-call request id, quiet third-party loggers by default.
3. Create `ApiClient` (shared `httpx.AsyncClient`).
4. Create `ReferenceCache`, do an initial `refresh()` (blocking), then spawn `cache.refresh_loop()` as a background `asyncio.Task`.
5. Publish everything as process-wide state: `state.app_state = AppState(settings, client, cache, refresh_task)` (`state.py`; `get_state()` raises if lifespan has not run).
6. Log whether HMAC signing is configured (key id + secret both non-empty).

On shutdown: cancel the refresh task, close the HTTP client, clear `app_state`.

### ASGI middleware — `McpOctetStreamJsonMiddleware`

Applied only to `POST /mcp`. Purpose: let the **OpenAI Platform MCP scanner** (and similarly sloppy clients) through FastMCP's strict header validation:

- Rewrites `Content-Type: application/octet-stream` → `application/json`.
- Ensures `Accept` contains both `application/json` and `text/event-stream` (adds/normalizes the header).
- Empty-body probes (`Content-Length` absent/0) get an immediate `204 No Content` without touching FastMCP.

### Custom HTTP routes

| Route | Method | Purpose |
|---|---|---|
| `/health` | GET | JSON: `ok`, `service`, `version` (package version), `api_upstream`, and `api_consumer` diagnostics (`code`, `key_id_configured`, truncated `key_id_hint`, `hmac_signing_configured`). Never exposes the secret. |
| `/.well-known/openai-apps-challenge` | GET | Serves `OPENAI_APPS_CHALLENGE_TOKEN` as plain text for OpenAI Apps domain verification; **404** when the env var is unset (no empty placeholder leak). |
| `/.well-known/oauth-protected-resource` (+ `/mcp` suffix/prefix variants — 3 routes) | GET | RFC 9728 protected-resource metadata: `resource` (= `OAUTH_RESOURCE_URL`), `authorization_servers` (= `OAUTH_AUTHORIZATION_SERVER`), `scopes_supported` (= `OAUTH_SCOPES`), `bearer_methods_supported: ["header"]`. |

## Auth layers

Auth is deliberately two-tier: **discovery is public, tool calls require a valid user token.**

### 1. Public discovery

MCP protocol requests that do not call tools (`initialize`, `tools/list`, `resources/list`, `prompts/list`) are served without authentication so ChatGPT / OpenAI Platform / Cursor can scan the server. No FastMCP `auth=` provider is installed on the app, so FastMCP itself does not gate requests.

### 2. Bearer validation on tool calls (`bearer_auth.py`)

`RideLoggerBearerMiddleware` is a FastMCP **MCP-level** middleware hooked on `on_call_tool`:

1. Reads the HTTP `Authorization: Bearer <JWT>` header from the current request (via `fastmcp.server.dependencies.get_http_request`; non-HTTP transports pass through).
2. If a bearer is present, validates it by calling upstream **`GET /api/auth/me`** with that token. A rejection returns a structured `ToolResult` error (`{"ok": false, "error": {"type": "bearer_auth", ...}}`) instead of raising.
3. On success, stores the token in a `ContextVar` (`_http_bearer_token`) for the duration of the call; tools retrieve it via `get_http_bearer_token()` inside `require_token()` (`tools/common.py`).

`require_token()` prefers the validated HTTP bearer; a hidden legacy `access_token` tool argument is still accepted for old non-HTTP clients but is excluded from MCP input schemas. The only tool that skips the token entirely is `reference_data_refresh` (server-side cache reload).

### 3. OAuth resource-server metadata (`auth_provider.py`)

- `OAUTH_SCOPES` — 8 scopes: `profile:read`, `vehicles:read/write`, `logs:read/write`, `files:read/write`, `reminders:read`.
- `RideLoggerTokenVerifier` — a FastMCP `TokenVerifier` that validates tokens against `GET /api/auth/me` and returns an `AccessToken` with `user_id` claim.
- `create_auth_provider()` — builds a `RemoteAuthProvider` (authorization server = ridelogger-api, resource = this server).

**Note:** `create_auth_provider()` is currently **not wired into the FastMCP app** — `app.py` does not pass `auth=` to `FastMCP(...)`. The OAuth story in production is: protected-resource metadata is served by the custom `/.well-known/oauth-protected-resource` routes, the client obtains a token from ridelogger-api's OAuth server, and the token is enforced per tool-call by `RideLoggerBearerMiddleware`. The provider module exists for a future switch to FastMCP-native auth.

## Upstream API client (`api_client.py`)

`ApiClient` wraps one shared `httpx.AsyncClient`:

- **Base URL**: `Settings.api_base` — `SK_API_URL` normalized to always end in `/api` (`config._normalize_api_base`).
- **Headers**: `Accept: application/json`; `X-Request-Id` (per-tool-call UUID from `logging_setup`); `Authorization: Bearer <token>` when a user token applies.
- **Methods**: `request()` (raw), `request_json()` (raises `UpstreamApiError` via `errors.raise_for_status`, returns parsed JSON or `None` on 204/empty), `request_bytes()` (downloads), `get_public_json()` (unauthenticated reference fetch with tenacity retry: 3 attempts, exponential backoff on timeouts/network errors).

### HMAC consumer signing

When both `API_CONSUMER_KEY_ID` and `API_CONSUMER_SECRET` are configured, every upstream request is signed (backward compatible: empty = unsigned):

| Header | Value |
|---|---|
| `X-Api-Consumer` | consumer code (default `mcp`) |
| `X-Api-Key-Id` | public key id |
| `X-Api-Timestamp` | Unix seconds |
| `X-Api-Nonce` | random UUIDv4 |
| `X-Api-Content-SHA256` | lowercase hex SHA-256 of the request body, or literal `UNSIGNED-PAYLOAD` for multipart uploads |
| `X-Api-Signature` | `v1=<hex HMAC-SHA256>` over the canonical string |

Canonical string (newline-joined): `METHOD \n request-target(path?query) \n timestamp \n nonce \n content-sha256`, keyed with the consumer secret. Verified by `tests/test_api_consumer_signing.py` against the ridelogger-api verification scheme.

### Error mapping (`errors.py`)

`raise_for_status()` converts non-2xx responses into `UpstreamApiError(status_code, message, body)`. The message combines the upstream `message`/`errors` payload with an actionable hint per status (401 reauthorize, 403 permission, 404 check ids, 422 validation, 429 rate limit, 5xx retry). For 402 the upstream body is never forwarded — the message is replaced with a neutral account-limit sentence (upstream 402 bodies contain account-tier/upsell wording that must not reach MCP clients). `tools/common.tool_error()` turns these into structured `{"ok": false, "error": {...}}` results, including Laravel field errors when present.

## Reference cache and resources

### `reference_cache.py` + `reference_paths.py`

`REFERENCE_PATHS` lists 14 public GET endpoints (countries, currencies, vehicle_types, vehicle_makes, fuel_types, fuel_units, charge_types, energy_units, powertrain_types, service_types, expense_types, mileage_units, steering_sides, fuel_consumption_units). `ReferenceCache`:

- `refresh()` — fetches all datasets concurrently (`asyncio.gather`, per-dataset failure tolerated and logged), stores data + metadata (`fetched_at`, `source_endpoint`).
- `refresh_loop()` — sleeps `REFERENCE_CACHE_TTL_SECONDS` (default **3600 s**) between refreshes; runs for the process lifetime.
- `envelope(name)` — returns `{data, fetched_at, ttl_seconds, source_endpoint}`.

### `resources.py`

Registers one MCP resource per dataset at **`ridelogger://reference/{name}`** (`application/json`, the envelope above) plus the policy resource **`ridelogger://policy/tool-semantics`** (see below). The tool `reference_data_refresh` forces a cache reload on demand.

## Tool semantics policy (`tool_semantics.py`)

Single source of truth for per-tool safety metadata, consumed both by MCP clients (as FastMCP annotations) and by the **ridelogger-ai orchestrator** (as an MCP resource).

- `REGISTERED_TOOL_NAMES` — frozenset of all 56 tool names; must match every `@mcp.tool` in `tools/*.py`.
- `TOOL_SEMANTICS` — maps each name to a policy dict (`kind`, `category` acquisition/execution, `mutation`, `confirmation` none/recommended/required, `risk`/`risk_level`, `side_effect_scope`, `idempotency`, `requires`, `provides`), built with `_read()` / `_write()` helpers.
- `MCP_NON_READ_ONLY_TOOLS` — currently only `reference_data_refresh` (mutates MCP server state, not user data).
- `MCP_DESTRUCTIVE_HINT_TOOLS` — updates/overwrites flagged destructive for ChatGPT Apps without raising RideLogger's internal risk level.
- `build_annotations()` / `get_annotations()` — derive FastMCP `ToolAnnotations`: `readOnlyHint` (no mutation and not in the non-read-only set), `destructiveHint` (risk `high` or listed in the destructive-hint set), `idempotentHint` (idempotency == `idempotent`), `openWorldHint=False` always. Each `@mcp.tool(annotations=get_annotations("name"))` fails fast (`KeyError`) if semantics are missing.
- `validate_registry()` — asserts the three sets are mutually consistent; called by `policy_resource_json()` and by tests.
- `policy_resource_json()` — the JSON body of `ridelogger://policy/tool-semantics`: `{ok, contract_version, uri, x_ridelogger, tools}`. `POLICY_CONTRACT_VERSION` (currently `2026-04-23.1`) is bumped when the envelope shape changes.

## Configuration (`config.py`)

All settings via pydantic-settings (`.env` file or environment; extra vars ignored). **No secret values here — see server `.env`.**

| Env var | Default | Purpose |
|---|---|---|
| `SK_API_URL` | — (**required**) | Upstream API base URL; `/api` suffix appended if missing |
| `REFERENCE_CACHE_TTL_SECONDS` | `3600` | Reference dataset refresh interval |
| `HTTP_TIMEOUT_S` | `30.0` | Upstream HTTP timeout |
| `HTTP_MAX_RETRIES` | `2` | Retry budget for `get_public_json` (attempts = value + 1; default 3 attempts) |
| `API_CONSUMER_CODE` | `mcp` | `X-Api-Consumer` header value |
| `API_CONSUMER_KEY_ID` | `""` | HMAC public key id; signing off when empty |
| `API_CONSUMER_SECRET` | `""` | HMAC signing secret; signing off when empty |
| `OAUTH_AUTHORIZATION_SERVER` | `https://api.ridelogger.com` | Advertised OAuth authorization server |
| `OAUTH_RESOURCE_URL` | `https://mcp.ridelogger.com/mcp` | Advertised protected resource URL |
| `OPENAI_APPS_CHALLENGE_TOKEN` | `""` | OpenAI Apps domain-verification token; challenge route 404s when empty |
| `MCP_HOST` | `0.0.0.0` | Bind address |
| `MCP_PORT` | `8083` | HTTP port |
| `LOG_LEVEL` | `INFO` | Python log level |
| `MCP_VERBOSE_LOGS` | `false` | When false, `mcp*` / `uvicorn.access` loggers are set to WARNING (Cursor polls ListTools frequently) |

## Tool layer conventions (`tools/`)

- One module per domain; each exposes `register(mcp)` called from `tools/__init__.register_all()`.
- Every tool returns `{"ok": true, "data": ...}` or `{"ok": false, "error": {...}}` (`tool_success` / `tool_error`).
- `sanitize_tool_data()` strips personal/internal fields recursively from responses (emails, names, tokens, sync UUIDs, `created_at`/`updated_at`, anything ending in `_token`/`_secret`, …) — MCP clients only see domain fields plus ids needed for follow-up calls.
- `body_from_kwargs()` / `compact_query_params()` drop `None` values so optional typed parameters are simply omitted upstream.
- Shared description snippets: `MONEY_LOGS_HINT` (multi-currency aggregation warning), `VEHICLE_REFS_HINT` and `LOG_REFS_HINT` (embedded reference objects in API v1.3+ responses).
- Write tools use **explicit typed parameters** mirrored from ridelogger-api FormRequest validation classes (e.g. `VehicleStoreRequest`, `FuelLogStoreRequest`) rather than opaque JSON blobs.

## Logging (`logging_setup.py`)

- Root logger format includes `rid=%(request_id)s`; a `ContextVar`-backed request id is generated per tool call (`new_request_id()` in `require_token`) and propagated upstream as `X-Request-Id`.
- Tokens are never logged.
- `httpx`/`httpcore` pinned to WARNING; `mcp*` and `uvicorn.access` are WARNING unless `MCP_VERBOSE_LOGS=true`.

## Testing (`tests/`, pytest + pytest-asyncio)

| Suite | What it locks down |
|---|---|
| `test_tool_annotations.py` | **Registry invariant**: `validate_registry()` passes; every registered tool has annotations; all non-mutating tools have `readOnlyHint=True`; all `risk="high"` tools have `destructiveHint=True`; `openWorldHint=False` everywhere; unknown names raise `KeyError`. Adding a tool without semantics fails CI. |
| `test_tool_dispatch_upstream.py` | Exercises every registered tool against a stubbed HTTP client — verifies method/path/params per tool. |
| `test_api_consumer_signing.py` | Canonical string + HMAC header construction, unsigned-payload handling for multipart. |
| `test_logs_list_query_params.py` | List-tool filters map to correct query params (`from`/`to`, `currency_id`, type ids). |
| `test_openai_apps_challenge.py` | Challenge route serves token / 404s when unset. |
| `test_reference_cache_paths.py` | Reference paths / cache envelope. |
| `test_response_sanitization.py` | `sanitize_tool_data` removes personal/internal keys. |

Run: `pip install -e ".[dev]" && pytest` (see README).

## Related documents

- `docs/FEATURES.md` — complete tool/resource catalog.
- `README.md` — configuration, run instructions, smoke tests.
- Deploy specifics live in `.cursor/rules/deploy.mdc` (not committed) and the production server.
