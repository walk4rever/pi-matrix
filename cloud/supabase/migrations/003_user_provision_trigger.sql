-- Trigger: call orchestrator when a new user registers
create or replace function pi_matrix_notify_orchestrator()
returns trigger as $$
begin
  perform net.http_post(
    url     := current_setting('app.pi_matrix_orchestrator_url'),
    headers := jsonb_build_object(
      'Content-Type',     'application/json',
      'x-webhook-secret', current_setting('app.pi_matrix_webhook_secret')
    ),
    body    := jsonb_build_object(
      'type',   TG_OP,
      'record', row_to_json(NEW)
    )::text
  );
  return NEW;
end;
$$ language plpgsql security definer;

create trigger pi_matrix_on_user_created
  after insert on auth.users
  for each row execute function pi_matrix_notify_orchestrator();
