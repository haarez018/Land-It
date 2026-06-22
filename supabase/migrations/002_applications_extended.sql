-- ============================================================
-- Land It — extend applications table with tracker fields
-- Run AFTER 001_initial.sql in Supabase SQL editor
-- ============================================================

alter table public.applications
  add column if not exists ats_score_before float,
  add column if not exists ats_score_after  float,
  add column if not exists priority         int     default 0,
  add column if not exists notes            text    default '',
  add column if not exists follow_up_due    timestamptz;
