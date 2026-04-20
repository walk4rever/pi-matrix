# Orchestrator

Manages cloud-hosted hermes instances — one container per user account.

## Responsibilities

- Provision a new instance when a user subscribes (cloud SKU)
- Inject user config and device token into the container
- Monitor instance health and restart on failure
- Tear down instance on subscription cancellation
- Rolling updates: pull new hermes version and restart per instance
