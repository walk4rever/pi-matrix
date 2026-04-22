#!/usr/bin/env bash
set -euo pipefail

# Migrate legacy per-user volumes:
#   pi-matrix-state-<user_id>
#   pi-matrix-skills-<user_id>
#   pi-matrix-workspace-<user_id>
# into the unified volume:
#   pi-matrix-hermes-<user_id>
# mounted at /root/.hermes.

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

copy_volume_into_subdir() {
  local src="$1"
  local dst="$2"
  local subdir="$3"
  run "docker run --rm \
    -v ${src}:/from:ro \
    -v ${dst}:/to \
    alpine:3.20 sh -lc 'mkdir -p /to/${subdir} && cp -a /from/. /to/${subdir}/'"
}

user_ids=$(docker volume ls --format '{{.Name}}' | \
  sed -nE 's/^pi-matrix-(state|skills|workspace)-(.+)$/\2/p' | sort -u)

if [[ -z "${user_ids}" ]]; then
  echo "No legacy volumes found. Nothing to migrate."
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
  new_vol="pi-matrix-hermes-${user_id}"
  state_vol="pi-matrix-state-${user_id}"
  skills_vol="pi-matrix-skills-${user_id}"
  workspace_vol="pi-matrix-workspace-${user_id}"

  echo "Migrating user: ${user_id}"

  if ! volume_exists "${new_vol}"; then
    run "docker volume create ${new_vol} >/dev/null"
    echo "  created ${new_vol}"
  fi

  if volume_exists "${state_vol}"; then
    copy_volume_into_subdir "${state_vol}" "${new_vol}" "state"
    echo "  copied ${state_vol} -> ${new_vol}/state"
    if $CLEANUP; then
      run "docker volume rm ${state_vol} >/dev/null"
      echo "  removed ${state_vol}"
    fi
  fi

  if volume_exists "${skills_vol}"; then
    copy_volume_into_subdir "${skills_vol}" "${new_vol}" "skills"
    echo "  copied ${skills_vol} -> ${new_vol}/skills"
    if $CLEANUP; then
      run "docker volume rm ${skills_vol} >/dev/null"
      echo "  removed ${skills_vol}"
    fi
  fi

  if volume_exists "${workspace_vol}"; then
    copy_volume_into_subdir "${workspace_vol}" "${new_vol}" "workspace"
    echo "  copied ${workspace_vol} -> ${new_vol}/workspace"
    if $CLEANUP; then
      run "docker volume rm ${workspace_vol} >/dev/null"
      echo "  removed ${workspace_vol}"
    fi
  fi

  echo
 done

echo "Migration complete."
if ! $CLEANUP; then
  echo "Legacy volumes were kept. Re-run with --cleanup after verification."
fi
