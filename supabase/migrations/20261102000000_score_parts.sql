-- Stage 5: score in two named parts, and restore restarts recency.
-- Additive: code already live ignores these columns.
alter table items
  add column if not exists restored_at timestamptz;

alter table daily_picks
  add column if not exists subject_points integer,
  add column if not exists recency_points integer;
