-- NecroCD schema: ghost telemetry, exorcism logs, resurrection metrics, audit trails.
create extension if not exists "pgcrypto";

create table if not exists public.ghost_telemetry (
  id uuid primary key default gen_random_uuid(),
  event_type text not null,
  repo text,
  branch text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists ghost_telemetry_created_idx on public.ghost_telemetry (created_at desc);
create index if not exists ghost_telemetry_type_idx on public.ghost_telemetry (event_type);

create table if not exists public.exorcism_logs (
  id uuid primary key default gen_random_uuid(),
  telemetry_id uuid references public.ghost_telemetry (id) on delete set null,
  repo text,
  file text not null,
  ok boolean not null default false,
  attempts integer not null default 0 check (attempts >= 0),
  findings jsonb not null default '[]'::jsonb,
  error text,
  latin_trace text,
  created_at timestamptz not null default now()
);
create index if not exists exorcism_logs_telemetry_idx on public.exorcism_logs (telemetry_id);
create index if not exists exorcism_logs_file_idx on public.exorcism_logs (file);
create index if not exists exorcism_logs_created_idx on public.exorcism_logs (created_at desc);

create table if not exists public.resurrection_metrics (
  id uuid primary key default gen_random_uuid(),
  repo text not null,
  pr_number integer,
  pr_url text,
  status text not null default 'open' check (status in ('open', 'merged', 'closed')),
  files_refactored integer not null default 0,
  findings_fixed integer not null default 0,
  exorcism_log_id uuid references public.exorcism_logs (id) on delete set null,
  opened_at timestamptz not null default now(),
  merged_at timestamptz
);
create index if not exists resurrection_metrics_repo_idx on public.resurrection_metrics (repo, status);
create index if not exists resurrection_metrics_exorcism_idx on public.resurrection_metrics (exorcism_log_id);

create table if not exists public.audit_trails (
  id uuid primary key default gen_random_uuid(),
  actor text not null,
  action text not null,
  target text,
  exorcism_log_id uuid references public.exorcism_logs (id) on delete set null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists audit_trails_created_idx on public.audit_trails (created_at desc);
create index if not exists audit_trails_actor_idx on public.audit_trails (actor);
create index if not exists audit_trails_exorcism_idx on public.audit_trails (exorcism_log_id);

-- Row level security: service role bypasses RLS; authenticated users get read-only access.
alter table public.ghost_telemetry enable row level security;
alter table public.exorcism_logs enable row level security;
alter table public.resurrection_metrics enable row level security;
alter table public.audit_trails enable row level security;

drop policy if exists "authenticated read telemetry" on public.ghost_telemetry;
create policy "authenticated read telemetry" on public.ghost_telemetry for select to authenticated using (true);
drop policy if exists "authenticated read exorcism" on public.exorcism_logs;
create policy "authenticated read exorcism" on public.exorcism_logs for select to authenticated using (true);
drop policy if exists "authenticated read metrics" on public.resurrection_metrics;
create policy "authenticated read metrics" on public.resurrection_metrics for select to authenticated using (true);
drop policy if exists "authenticated read audit" on public.audit_trails;
create policy "authenticated read audit" on public.audit_trails for select to authenticated using (true);

-- Realtime publication for the live dashboard.
do $$
begin
  if not exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    create publication supabase_realtime;
  end if;
end $$;
do $$
declare t text;
begin
  foreach t in array array['ghost_telemetry', 'exorcism_logs', 'resurrection_metrics'] loop
    if not exists (select 1 from pg_publication_tables
                   where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;
