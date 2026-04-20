-- Multi-tenant schema: all tables scoped by user_id
-- RLS enforces data isolation at the database level

-- Devices: each user can have one or more Mac mini devices
create table devices (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  token       text not null unique,  -- device auth token
  version     text,                  -- installed hermes version
  last_seen   timestamptz,
  created_at  timestamptz not null default now()
);

-- User config: hermes + IM platform settings
create table user_configs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  platform    text not null default 'feishu',  -- feishu | wecom | weixin
  config      jsonb not null default '{}',
  updated_at  timestamptz not null default now()
);

-- Memory: cross-session context per user
create table memories (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  device_id   uuid references devices(id) on delete set null,
  content     text not null,
  embedding   vector(1536),          -- for semantic search (pgvector)
  created_at  timestamptz not null default now()
);

-- RLS: users can only access their own rows
alter table devices      enable row level security;
alter table user_configs enable row level security;
alter table memories     enable row level security;

create policy "users own their devices"
  on devices for all using (auth.uid() = user_id);

create policy "users own their configs"
  on user_configs for all using (auth.uid() = user_id);

create policy "users own their memories"
  on memories for all using (auth.uid() = user_id);

-- Indexes
create index on devices      (user_id);
create index on user_configs (user_id);
create index on memories     (user_id);
create index on devices      (token);
