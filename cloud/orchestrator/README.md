# Orchestrator

Manages cloud-hosted hermes instances — one container per user account.

## Responsibilities

- Provision a new instance when a user subscribes (cloud SKU)
- Inject user config and device token into the container
- Monitor instance health and restart on failure
- Tear down instance on subscription cancellation
- Rolling updates: pull new hermes version and restart per instance

## Upgrade model

Executor images are immutable and pinned to a Hermes release tag.

- Build images with `deploy/scripts/build-hermes-images.sh v2026.4.30`
- Set `EXECUTOR_IMAGE=pi-matrix/executor:hermes-v2026.4.30`
- Set `HERMES_VERSION=v2026.4.30`
- Trigger a dry run:

```bash
DRY_RUN=true \
ORCHESTRATOR_URL=http://127.0.0.1:8081 \
GATEWAY_KEY=... \
deploy/scripts/upgrade-executors.sh
```

- Trigger a canary for one user:

```bash
USER_IDS=<user-uuid> \
ORCHESTRATOR_URL=http://127.0.0.1:8081 \
GATEWAY_KEY=... \
deploy/scripts/upgrade-executors.sh
```

Upgrade behavior:

- Pulls the target executor image when `DOCKER_PULL_ON_UPGRADE=true`
- Snapshots `pi-matrix-home-<user_id>` to `EXECUTOR_UPGRADE_BACKUP_DIR`
- Replaces the user container with the new image
- Waits for `/health`
- Records `executor_image`, `hermes_version`, previous image/version, backup path, and status in `pi_matrix_devices`
- If health fails, recreates the container with the previous image

## Storage model (current)

Each user container mounts a single persistent Docker volume to `/root`:

- `pi-matrix-home-<user_id> -> /root`

This keeps **all** Hermes runtime data durable across container recreation:
state DB, skills, memories, workspace files, config, SOUL, and user-created files.

## Legacy volume migration

If you previously used split volumes (`state/skills/workspace`), migrate with:

```bash
./deploy/scripts/migrate-hermes-home-volume.sh --dry-run
./deploy/scripts/migrate-hermes-home-volume.sh
# after verification
./deploy/scripts/migrate-hermes-home-volume.sh --cleanup
```
