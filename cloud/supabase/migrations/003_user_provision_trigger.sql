-- Trigger: call orchestrator webhook when a new user registers
-- Supabase uses pg_net extension for HTTP calls from triggers

create or replace function notify_orchestrator()
returns trigger as $$
begin
  perform net.http_post(
    url     := current_setting('app.orchestrator_webhook_url'),
    headers := jsonb_build_object(
      'Content-Type',      'application/json',
      'x-webhook-secret',  current_setting('app.orchestrator_webhook_secret')
    ),
    body    := jsonb_build_object(
      'type',   TG_OP,
      'record', row_to_json(NEW)
    )::text
  );
  return NEW;
end;
$$ language plpgsql security definer;

create trigger on_user_created
  after insert on auth.users
  for each row execute function notify_orchestrator();
