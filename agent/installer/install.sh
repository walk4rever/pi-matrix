#!/usr/bin/env bash
# Installs hermes-agent at the pinned version onto Mac mini

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(cat "$SCRIPT_DIR/hermes.version" | tr -d '[:space:]')"
if [[ "$VERSION" == v* ]]; then
  HERMES_REF="$VERSION"
else
  HERMES_REF="v${VERSION}"
fi
HERMES_REPO="https://github.com/nousresearch/hermes-agent"
INSTALL_DIR="$HOME/.hermes"

echo "Installing hermes-agent ${HERMES_REF} ..."

if [ -d "$INSTALL_DIR" ]; then
  echo "Existing install found at $INSTALL_DIR, updating..."
  git -C "$INSTALL_DIR" fetch --tags
  git -C "$INSTALL_DIR" checkout "${HERMES_REF}"
else
  git clone --depth 1 --branch "${HERMES_REF}" "$HERMES_REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
pip install -e . --quiet

echo "hermes-agent ${HERMES_REF} installed."
