-- ============================================================
-- Land It — initial schema
-- Run this in Supabase SQL editor (Dashboard → SQL Editor)
-- ============================================================

-- ── Profiles (auto-created on signup via trigger) ─────────────
create table if not exists public.profiles (
  id          uuid primary key references auth.users on delete cascade,
  email       text unique not null,
  full_name   text,
  avatar_url  text,
  created_at  timestamptz default now()
);

alter table public.profiles enable row level security;
create policy "Users own their profile"
  on public.profiles for all using (auth.uid() = id);

-- ── Job queue (one row per job per user) ─────────────────────
create table if not exists public.jobs (
  id          text primary key,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  data        jsonb not null,          -- full JobDescription serialised
  source_url  text,
  created_at  timestamptz default now(),
  unique (user_id, source_url)         -- dedup per user
);

alter table public.jobs enable row level security;
create policy "Users own their jobs"
  on public.jobs for all using (auth.uid() = user_id);

create index jobs_user_id_idx on public.jobs (user_id);

-- ── Applications tracker ──────────────────────────────────────
create table if not exists public.applications (
  id           text primary key,
  user_id      uuid not null references public.profiles(id) on delete cascade,
  job_id       text not null,
  job_snapshot jsonb,                  -- snapshot of job at time of apply
  status       text not null default 'submitted',
  fit_score    float,
  submitted_at timestamptz,
  created_at   timestamptz default now()
);

alter table public.applications enable row level security;
create policy "Users own their applications"
  on public.applications for all using (auth.uid() = user_id);

create index applications_user_id_idx on public.applications (user_id);

-- ── Apply-click tracking (distinct job clicks) ────────────────
create table if not exists public.apply_clicks (
  user_id    uuid not null references public.profiles(id) on delete cascade,
  job_id     text not null,
  title      text,
  company    text,
  created_at timestamptz default now(),
  primary key (user_id, job_id)
);

alter table public.apply_clicks enable row level security;
create policy "Users own their clicks"
  on public.apply_clicks for all using (auth.uid() = user_id);

-- ── Auto-create profile row on new signup ─────────────────────
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
