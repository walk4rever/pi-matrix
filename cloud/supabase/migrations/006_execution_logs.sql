-- Execution logs for user dashboard visibility
create table if not exists pi_matrix_execution_logs (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  open_id         text not null,
  session_id      text,
  request_text    text not null default '',
  status          text not null default 'success', -- success | failed
  error_code      text,
  error_message   text,
  response_preview text,
  files_count     int not null default 0,
  created_at      timestamptz not null default now()
);

alter table pi_matrix_execution_logs enable row level security;

create policy "users own execution logs"
  on pi_matrix_execution_logs for select
  using (auth.uid() = user_id);

grant select, insert, update, delete on pi_matrix_execution_logs to service_role;
grant select on pi_matrix_execution_logs to authenticated;

create index if not exists pi_matrix_execution_logs_user_created_idx
  on pi_matrix_execution_logs (user_id, created_at desc);
