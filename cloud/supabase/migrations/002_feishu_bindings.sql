-- Feishu open_id <-> pi-matrix user binding
create table feishu_bindings (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  open_id    text not null unique,
  created_at timestamptz not null default now()
);

alter table feishu_bindings enable row level security;

create policy "users own their bindings"
  on feishu_bindings for all using (auth.uid() = user_id);

create index on feishu_bindings (open_id);

-- Add instance_type and endpoint to devices
alter table devices
  add column instance_type text not null default 'mac',  -- mac | cloud
  add column endpoint      text;                          -- cloud instances only
