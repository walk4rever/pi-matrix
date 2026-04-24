# Platform Gateway

Central multi-tenant gateway for pi-matrix. Replaces the old `router` + `hermes_wrapper` pair.

## Responsibilities

- **Feishu message ingestion** — WebSocket via Hermes `FeishuAdapter`
- **Session management** — JSONL transcript store with automatic compression (hygiene)
- **Command interception** — `/reset`, `/compact`, `/help`, `/status`
- **Agent routing** — HTTP to stateless per-user `executor` containers
- **Message delivery** — Text via `FeishuAdapter`, files via `lark_oapi` / Feishu Drive / Cloudflare R2 fallback

## Security

- **Feishu credentials (`app_id`, `app_secret`) live ONLY in this service**
- User containers (`executor`) hold **zero** Feishu credentials
- Internal `/internal/notify` endpoint is protected by `x-internal-secret` (shared key)

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | FeishuAdapter connection status |
| `GET /metrics` | Counters: received, sent, errors, timeouts, compressed |
| `POST /internal/notify` | Called by `api` service to send Feishu messages |

## Environment

See `.env.example`.

Key variables:
- `FEISHU_APP_ID`, `FEISHU_APP_SECRET` — bot credentials
- `GATEWAY_URL`, `GATEWAY_KEY` — LiteLLM Proxy (used for session compression)
- `SESSIONS_DIR` — local path for JSONL transcripts
- `SESSION_TOKEN_LIMIT` — compression threshold (default 6000 tokens)
- `ALLOWED_USERS` — optional comma-separated open_id allowlist
- `R2_*` — optional Cloudflare R2 fallback for large files when Drive is unavailable

## Session Hygiene

When a transcript exceeds `SESSION_TOKEN_LIMIT`, old messages (except the most recent `SESSION_KEEP_RECENT`) are summarized by an LLM call through the LiteLLM Gateway. The summary replaces the old history, keeping the session cheap and fast.

Users can also trigger compression manually with `/compact`.

## Idle Cleanup

A background task runs every hour and deletes session metadata + transcripts that have been idle for >7 days.
