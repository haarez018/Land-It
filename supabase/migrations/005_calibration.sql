-- ============================================================
-- Land It — add callback_probability to applications
-- Run AFTER 004_ab_testing.sql in Supabase SQL editor
-- ============================================================

alter table public.applications
  add column if not exists callback_probability float;
