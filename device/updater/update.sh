#!/usr/bin/env bash
# Called by cloud monitor to update hermes to a new pinned version

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW_VERSION="${1:-}"

if [ -z "$NEW_VERSION" ]; then
  echo "Usage: update.sh <version>" >&2
  exit 1
fi

echo "$NEW_VERSION" > "$SCRIPT_DIR/../installer/hermes.version"

"$SCRIPT_DIR/../installer/install.sh"

# Restart the hermes service
launchctl stop com.pi-matrix.hermes
launchctl start com.pi-matrix.hermes

echo "Updated to v${NEW_VERSION} and restarted."
