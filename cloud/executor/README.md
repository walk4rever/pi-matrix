# Agent Executor

Stateless turn runner for pi-matrix. One container per user, launched by the orchestrator.

## Responsibilities

- Receive a turn payload (`history`, `message`, `attachments`) from `platform-gateway`
- Run Hermes `AIAgent.run_conversation()` with the provided history
- Return `response` text + base64-encoded `files` found in the response
- **No session persistence, no Feishu credentials, no platform logic**

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /execute` | Run one agent turn |
| `GET /health` | Liveness probe |

## Environment

- `GATEWAY_URL` / `GATEWAY_KEY` — LiteLLM Proxy
- `HERMES_MODEL` — model alias (default: "default")
- `HERMES_WORKSPACE_DIR` — workspace for uploads / tool outputs

## Attachments

Files sent by the user through Feishu are forwarded by `platform-gateway` as base64 blobs in the `attachments` field. The executor materializes them to `HERMES_WORKSPACE_DIR/uploads/` before running the agent.

## File Collection

After the agent turn completes, the executor scans the response text for absolute file paths (`/...`) and inlines any files ≤20 MB as base64 in the response payload. `platform-gateway` decodes and delivers them back to the user.

## Feishu Toolsets

`feishu_doc` and `feishu_drive` are enabled. `platform-gateway` forwards user-scoped Feishu tokens on each turn, and the executor injects them into Hermes runtime env before execution.
