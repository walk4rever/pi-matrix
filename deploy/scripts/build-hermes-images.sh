#!/usr/bin/env bash
set -euo pipefail

# Build pi-matrix images against a pinned Hermes tag.
#
# Usage:
#   deploy/scripts/build-hermes-images.sh [v2026.4.30] [pi-matrix]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERMES_REF="${1:-v2026.4.30}"
IMAGE_PREFIX="${2:-pi-matrix}"

executor_image="${IMAGE_PREFIX}/executor:hermes-${HERMES_REF}"
message_image="${IMAGE_PREFIX}/message:hermes-${HERMES_REF}"

echo "Building ${executor_image}"
docker build \
  --build-arg "HERMES_REF=${HERMES_REF}" \
  -t "${executor_image}" \
  "${ROOT_DIR}/cloud/executor"

echo "Building ${message_image}"
docker build \
  --build-arg "HERMES_REF=${HERMES_REF}" \
  -t "${message_image}" \
  "${ROOT_DIR}/cloud/message"

cat <<EOF

Built images:
  ${executor_image}
  ${message_image}

Set:
  HERMES_VERSION=${HERMES_REF}
  EXECUTOR_IMAGE=${executor_image}

Compose override example:
  docker compose -f deploy/docker-compose.yml build --build-arg HERMES_REF=${HERMES_REF} message
EOF
