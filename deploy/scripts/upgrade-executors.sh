#!/usr/bin/env bash
set -euo pipefail

# Trigger orchestrator rolling upgrade for cloud executor containers.
#
# Required env:
#   ORCHESTRATOR_URL  e.g. http://127.0.0.1:8081
#   GATEWAY_KEY       same secret used by orchestrator x-webhook-secret
#
# Optional env:
#   EXECUTOR_IMAGE    default pi-matrix/executor:hermes-v2026.4.30
#   HERMES_VERSION    default v2026.4.30
#   USER_IDS          comma-separated user UUIDs; omitted means all cloud users
#   DRY_RUN           true|false

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:8081}"
EXECUTOR_IMAGE="${EXECUTOR_IMAGE:-pi-matrix/executor:hermes-v2026.4.30}"
HERMES_VERSION="${HERMES_VERSION:-v2026.4.30}"
DRY_RUN="${DRY_RUN:-false}"
USER_IDS="${USER_IDS:-}"
export EXECUTOR_IMAGE HERMES_VERSION DRY_RUN USER_IDS

payload="$(python3 - <<'PY'
import json
import os

user_ids = [item.strip() for item in os.environ.get("USER_IDS", "").split(",") if item.strip()]
payload = {
    "image": os.environ["EXECUTOR_IMAGE"],
    "hermes_version": os.environ["HERMES_VERSION"],
    "dry_run": os.environ.get("DRY_RUN", "false").lower() == "true",
    "backup": True,
}
if user_ids:
    payload["user_ids"] = user_ids
print(json.dumps(payload))
PY
)"

curl -fsS \
  -X POST "${ORCHESTRATOR_URL%/}/executors/upgrade" \
  -H "Content-Type: application/json" \
  -H "x-webhook-secret: ${GATEWAY_KEY:?GATEWAY_KEY is required}" \
  -d "${payload}"
