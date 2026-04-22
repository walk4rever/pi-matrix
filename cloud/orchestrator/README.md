# Orchestrator

Manages cloud-hosted hermes instances — one container per user account.

## Responsibilities

- Provision a new instance when a user subscribes (cloud SKU)
- Inject user config and device token into the container
- Monitor instance health and restart on failure
- Tear down instance on subscription cancellation
- Rolling updates: pull new hermes version and restart per instance

## Storage model (current)

Each user container mounts a single persistent Docker volume to `/root/.hermes`:

- `pi-matrix-hermes-<user_id> -> /root/.hermes`

This keeps **all** Hermes runtime data durable across container recreation:
state DB, skills, memories, workspace files, config, and SOUL.

## Legacy volume migration

If you previously used split volumes (`state/skills/workspace`), migrate with:

```bash
./deploy/scripts/migrate-hermes-home-volume.sh --dry-run
./deploy/scripts/migrate-hermes-home-volume.sh
# after verification
./deploy/scripts/migrate-hermes-home-volume.sh --cleanup
```
