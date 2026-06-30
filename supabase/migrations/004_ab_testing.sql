-- ============================================================
-- Land It — A/B test results persistence
-- Run AFTER 003_resumes.sql in Supabase SQL editor
-- ============================================================

create table if not exists public.ab_tests (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.profiles(id) on delete cascade,
  resume_a_id  text not null,
  resume_b_id  text not null,
  job_id       text not null,
  score_a      float,
  score_b      float,
  winner       text,
  dimensions_a jsonb,
  dimensions_b jsonb,
  created_at   timestamptz default now()
);

alter table public.ab_tests enable row level security;
create policy "Users own their ab_tests"
  on public.ab_tests for all using (auth.uid() = user_id);

create index ab_tests_user_id_idx on public.ab_tests (user_id);
