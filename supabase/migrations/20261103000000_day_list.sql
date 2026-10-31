-- Stage 6: the day's list has a short and a long section, and links that fell
-- off since the last list are kept with their cause. Additive: code already
-- live ignores the new column and table.
alter table daily_picks
  add column if not exists section varchar(8);

create table if not exists fallen_off (
  id bigint generated always as identity primary key,
  run_on date not null,
  item_id bigint not null references items (id) on delete cascade,
  cause varchar(16) not null,
  points_before double precision not null,
  points_after integer,
  unique (run_on, item_id)
);

create index if not exists fallen_off_run_on_idx on fallen_off (run_on desc);

alter table fallen_off enable row level security;
revoke all on table fallen_off from anon, authenticated;
grant all on table fallen_off to service_role;
