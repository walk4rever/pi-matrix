-- pi-matrix tables, prefixed to coexist with other projects in shared Supabase

create table pi_matrix_devices (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  name          text not null,
  token         text not null unique,
  instance_type text not null default 'mac',  -- mac | cloud
  endpoint      text,
  version       text,
  last_seen     timestamptz,
  created_at    timestamptz not null default now()
);

create table pi_matrix_user_configs (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  platform   text not null default 'feishu',
  config     jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

create table pi_matrix_memories (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  device_id  uuid references pi_matrix_devices(id) on delete set null,
  content    text not null,
  created_at timestamptz not null default now()
);

create table pi_matrix_feishu_bindings (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade,
  open_id    text not null unique,
  created_at timestamptz not null default now()
);

-- RLS
alter table pi_matrix_devices         enable row level security;
alter table pi_matrix_user_configs    enable row level security;
alter table pi_matrix_memories        enable row level security;
alter table pi_matrix_feishu_bindings enable row level security;

create policy "users own their devices"
  on pi_matrix_devices for all using (auth.uid() = user_id);
create policy "users own their configs"
  on pi_matrix_user_configs for all using (auth.uid() = user_id);
create policy "users own their memories"
  on pi_matrix_memories for all using (auth.uid() = user_id);
create policy "users own their feishu bindings"
  on pi_matrix_feishu_bindings for all using (auth.uid() = user_id);

-- Grants
grant usage on schema public to anon, authenticated, service_role;
grant select, insert, update, delete on pi_matrix_devices         to authenticated, service_role;
grant select, insert, update, delete on pi_matrix_user_configs    to authenticated, service_role;
grant select, insert, update, delete on pi_matrix_memories        to authenticated, service_role;
grant select, insert, update, delete on pi_matrix_feishu_bindings to authenticated, service_role;

-- Unique constraints
alter table pi_matrix_devices add constraint pi_matrix_devices_user_name_unique unique (user_id, name);

-- Indexes
create index on pi_matrix_devices         (user_id);
create index on pi_matrix_devices         (token);
create index on pi_matrix_user_configs    (user_id);
create index on pi_matrix_memories        (user_id);
create index on pi_matrix_feishu_bindings (open_id);
