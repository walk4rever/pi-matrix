-- Track cloud executor image/Hermes version upgrades for rollback and audit.

alter table pi_matrix_devices
  add column if not exists executor_image text,
  add column if not exists previous_executor_image text,
  add column if not exists hermes_version text,
  add column if not exists previous_hermes_version text,
  add column if not exists last_upgrade_at timestamptz,
  add column if not exists last_upgrade_status text,
  add column if not exists last_upgrade_error text,
  add column if not exists last_upgrade_backup_path text;

create index if not exists pi_matrix_devices_cloud_upgrade_status_idx
  on pi_matrix_devices (instance_type, last_upgrade_status);
