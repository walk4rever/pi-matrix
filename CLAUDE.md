# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

pi-matrix is an edge-cloud "AI employee" platform. Users talk to their agent through Feishu; the agent runtime is [hermes-agent](https://github.com/NousResearch/hermes-agent) (a pinned dependency, **never forked or patched here**) running either in a per-user cloud container or on a user's Mac mini. This repo contains the platform around Hermes: message ingestion, session management, container orchestration, LLM gateway config, the user dashboard, and deployment scripts.

**The project keeps exactly three docs — `README.md`, `PRODUCT.md`, `TODO.md`. Do not create others.** `PRODUCT.md` (gitignored, internal) is the design-of-record: positioning, pricing, architecture, and design decisions. `TODO.md` is the active work queue — unfinished items only, P0–P3; when something ships, its conclusion is written back into `PRODUCT.md` and removed from here. `CLAUDE-DESIGN.md` is a pre-existing design system reference for the dashboard UI (warm parchment palette, serif headlines, terracotta `#c96442` accent) — read it before touching dashboard UI.

Two product lines run in parallel. The **Hermes line** (`cloud/message`, `cloud/executor`, Feishu channel) is described below and is currently **frozen** — do not change its contracts. The **pi line** (cloud instances of pi-coding-agent driven from web/desktop, with per-instance sandboxing and TokenEconBench measurement) is designed but not implemented; see `PRODUCT.md` § "pi Track" before starting any work under `cloud/pi/` or `bench/`.

## Commands

Backend (run from `deploy/`, requires `deploy/.env` — see `.env.example`):

```bash
docker compose up -d                       # all services: gateway, message, api, orchestrator
docker compose up -d --build message       # rebuild + restart one service
docker compose logs -f message             # tail a service
```

Build Hermes-pinned images (executor + message are built against a Hermes release tag):

```bash
deploy/scripts/build-hermes-images.sh v2026.4.30      # → pi-matrix/{executor,message}:hermes-v2026.4.30
```

Roll cloud executors onto a new image (orchestrator does snapshot → replace → health check → auto-rollback):

```bash
DRY_RUN=true ORCHESTRATOR_URL=http://127.0.0.1:8081 GATEWAY_KEY=... deploy/scripts/upgrade-executors.sh
USER_IDS=<uuid>  ORCHESTRATOR_URL=http://127.0.0.1:8081 GATEWAY_KEY=... deploy/scripts/upgrade-executors.sh   # canary
```

Dashboard (`cloud/dashboard/`, deployed on Vercel):

```bash
npm install && npm run dev                 # local dev
npm run build                              # must pass before pushing — Vercel builds on push
```

LLM gateway standalone: `pip install 'litellm[proxy]' && litellm --config cloud/gateway/config.yaml --port 4000`

Database migrations: SQL files in `cloud/supabase/migrations/`, applied manually against the shared Supabase project (no migration runner). Number new files sequentially.

There is no test suite and no linter configured. Verify changes by rebuilding the affected container and exercising the endpoint (`/health`, `/metrics`) or the Feishu flow.

## Architecture

### Request path (cloud SKU)

```
Feishu user
  → message (pi-matrix-message)          # Hermes FeishuAdapter over WebSocket
      resolve open_id → user_id → device.endpoint (Supabase, 30s in-memory cache)
      load JSONL transcript, compress if over token budget, intercept /reset /compact /help /status
      POST {endpoint}/execute            # 3 attempts, exponential backoff
  → executor (pi-matrix-<user_id>)       # stateless Hermes AIAgent.run_conversation()
      → gateway (pi-matrix-llm)          # LiteLLM Proxy, model aliases "default" / "vision"
  ← response text + base64 files
  → message delivers: text via FeishuAdapter, files via lark_oapi → user Feishu Drive → Cloudflare R2
```

`api` (FastAPI, behind nginx at `/pm/api/`) serves the dashboard and device endpoints; `orchestrator` (nginx `/pm/internal/`, localhost-only) owns container lifecycle via the mounted Docker socket. All containers share the `pi-matrix` Docker network and address each other by container name.

### Service boundaries that matter

- **Feishu credentials (`FEISHU_APP_ID`/`SECRET`) live only in `message` (and `api`, for the Drive OAuth callback). Executor containers hold zero Feishu credentials** — user-scoped Drive tokens are fetched by `message` per turn and passed in the `user_tokens` field of the execute payload, where the executor injects them into Hermes runtime env.
- Executors are **stateless per turn**: history arrives in the request, nothing about the conversation is persisted inside `/execute`. Session state (JSONL transcripts + metadata) lives in `message` under `SESSIONS_DIR`.
- Internal calls are authenticated by a single shared secret: `GATEWAY_KEY` / `GATEWAY_MASTER_KEY` doubles as the orchestrator's `x-webhook-secret`, the `message` `/internal/notify` `x-internal-secret`, and the LiteLLM master key.
- `cloud/gateway/` is the **LLM** gateway (LiteLLM). `cloud/message/` is the platform gateway — older docs and code call it "platform-gateway"; the directory, service, and hostname were renamed to `message`, but internal variables like `PLATFORM_GATEWAY_URL` remain.
- `cloud/memory/` and `cloud/monitor/` are README-only placeholders, not implemented services.

### Per-user storage and upgrades

Each cloud user gets one Docker volume `pi-matrix-home-<user_id>` mounted at `/root` in container `pi-matrix-<user_id>` — this holds *everything* durable (Hermes state DB, memories, skills, workspace, SOUL.md, user files). Executor images are immutable and pinned to a Hermes tag; upgrading means replacing the container while keeping the volume. `orchestrator/containers.py` snapshots the volume to `EXECUTOR_UPGRADE_BACKUP_DIR` before replacing and rolls back to the previous image if `/health` doesn't come up. Upgrade metadata (image, hermes_version, previous values, backup path, status) is recorded on `pi_matrix_devices`.

Hermes version is pinned in three places that must stay in sync: `agent/installer/hermes.version` (Mac mini), the `HERMES_REF` build arg / `HERMES_VERSION` env, and the `EXECUTOR_IMAGE` tag.

### Memory and personality flow

`SOUL.md` (personality) and `memories/USER.md` + `memories/MEMORY.md` are files inside the executor's `/root/.hermes/`, and simultaneously mirrored in Supabase so the dashboard can show and edit them while the container is offline:

- Dashboard write → `api` upserts to DB, then best-effort `PUT {executor}/files/{SOUL|USER|MEMORY}`.
- After each successful turn → `message` fire-and-forget `GET {executor}/files/...` and upserts back to DB.

The executor reads SOUL.md from disk via Hermes; it does not consume the `ephemeral_system_prompt` field that `message` includes in the payload.

### Database conventions (shared Supabase project)

All tables are prefixed `pi_matrix_` because the project shares a Supabase instance with other apps. Tables: `pi_matrix_devices`, `pi_matrix_user_configs`, `pi_matrix_memories`, `pi_matrix_feishu_bindings`, `pi_matrix_execution_logs`, `pi_matrix_user_credentials`.

`pi_matrix_user_credentials` is the unified key-value credential store — `(user_id, provider, credential_key)` is the uniqueness constraint, so **every upsert must pass `on_conflict="user_id,provider,credential_key"`**. It carries both real credentials (`provider='feishu_drive'`) and mirrored content (`provider` in `soul_md`, `user_md`, `memory_md`, with `credential_key='content'`). It is service-role-only (RLS policy `USING (false)`); other tables use `auth.uid() = user_id` RLS and are reachable from the dashboard with the anon key. Backend services use the service key and bypass RLS.

The legacy `pi_matrix_feishu_drive_tokens` table still has read fallbacks in `cloud/message/main.py`; they are transitional and can go once all environments are migrated.

## Conventions

- Backend services are FastAPI + `pydantic-settings`; each service owns a flat module layout (`main.py`, `config.py`, ...) except `api`, which uses `app/routers/`, `app/middleware/`.
- Every service reads config from the same `deploy/.env` (`env_file: .env` in compose); per-service `.env.example` files document the subset each one uses.
- Network calls to executors, Feishu, and Supabase are wrapped in try/except that logs and degrades — a failed memory sync, Drive upload, or execution-log write must never break the user's turn. Match that pattern.
- User-facing strings in `message`, `api`, and the dashboard are Chinese; code comments and logs are English.
- Bump `cloud/dashboard/package.json` version when shipping dashboard changes; commits follow `type(scope): description`.
