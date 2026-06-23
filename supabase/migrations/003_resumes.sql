-- ============================================================
-- Land It — resumes table
-- Run AFTER 002_applications_extended.sql in Supabase SQL editor
-- ============================================================

create table if not exists public.resumes (
  id          text primary key,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  data        jsonb not null,          -- full Resume object serialised
  filename    text,
  created_at  timestamptz default now()
);

alter table public.resumes enable row level security;
create policy "Users own their resumes"
  on public.resumes for all using (auth.uid() = user_id);

create index resumes_user_id_idx on public.resumes (user_id);
