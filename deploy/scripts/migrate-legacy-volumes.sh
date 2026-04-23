#!/usr/bin/env bash
set -euo pipefail

# Migrate legacy per-user volumes into the unified home volume:
#   pi-matrix-hermes-<user_id>  ->  pi-matrix-home-<user_id>
# The new executor mounts pi-matrix-home-<user_id> at /root.

CLEANUP=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cleanup)
      CLEANUP=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown arg: $1" >&2
      echo "Usage: $0 [--dry-run] [--cleanup]" >&2
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found" >&2
  exit 1
fi

run() {
  if $DRY_RUN; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

volume_exists() {
  docker volume inspect "$1" >/dev/null 2>&1
}

copy_volume() {
  local src="$1"
  local dst="$2"
  run "docker run --rm \
    -v ${src}:/from:ro \
    -v ${dst}:/to \
    alpine:3.20 sh -lc 'cp -a /from/. /to/'"
}

user_ids=$(docker volume ls --format '{{.Name}}' | \
  sed -nE 's/^pi-matrix-hermes-(.+)$/\1/p' | sort -u)

if [[ -z "${user_ids}" ]]; then
  echo "No legacy pi-matrix-hermes-* volumes found. Nothing to migrate."
  exit 0
fi

echo "Users to migrate:"
echo "${user_ids}" | sed 's/^/  - /'

running=$(docker ps --format '{{.Names}}' | sed -nE 's/^pi-matrix-(.+)$/\1/p' | sort -u)
if [[ -n "${running}" ]]; then
  echo
  echo "WARNING: active user containers detected (recommended: stop before migration):"
  echo "${running}" | sed 's/^/  - /'
fi

echo
for user_id in ${user_ids}; do
  old_vol="pi-matrix-hermes-${user_id}"
  new_vol="pi-matrix-home-${user_id}"

  echo "Migrating user: ${user_id}"

  if ! volume_exists "${new_vol}"; then
    run "docker volume create ${new_vol} >/dev/null"
    echo "  created ${new_vol}"
  fi

  if volume_exists "${old_vol}"; then
    copy_volume "${old_vol}" "${new_vol}"
    echo "  copied ${old_vol} -> ${new_vol}"
    if $CLEANUP; then
      run "docker volume rm ${old_vol} >/dev/null"
      echo "  removed ${old_vol}"
    fi
  fi

done

echo
echo "Migration complete."
if ! $CLEANUP; then
  echo "Legacy volumes were kept. Re-run with --cleanup after verification."
fi
