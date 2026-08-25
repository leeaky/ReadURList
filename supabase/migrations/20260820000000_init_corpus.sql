-- ReadURList corpus: items, clusters, daily picks, digest runs.
-- RLS enabled with no policies: Data API is denied; the worker and
-- Vercel server use the service role (bypasses RLS).

create extension if not exists "pgcrypto";

create table if not exists items (
  id bigint generated always as identity primary key,
  url varchar(2048) not null unique,
  title varchar(1024) not null,
  snapshot text not null default '',
  subject varchar(256) not null default '',
  topics text[] not null default '{}',
  keywords text[] not null default '{}',
  extracted_text text not null default '',
  priority integer not null default 3,
  note text,
  similar_to_item_id bigint references items (id),
  created_at timestamptz not null default now(),
  read_at timestamptz,
  summary_one_liner varchar(1024) not null default '',
  surfaced_count integer not null default 0
);

create index if not exists items_created_at_idx on items (created_at desc);
create index if not exists items_read_at_idx on items (read_at);
create index if not exists items_subject_idx on items (subject);

create table if not exists clusters (
  id bigint generated always as identity primary key,
  label varchar(256) not null,
  computed_at timestamptz not null default now()
);

create table if not exists cluster_items (
  cluster_id bigint not null references clusters (id) on delete cascade,
  item_id bigint not null references items (id) on delete cascade,
  primary key (cluster_id, item_id)
);

create table if not exists daily_picks (
  id bigint generated always as identity primary key,
  run_on date not null,
  item_id bigint not null references items (id),
  rank integer not null,
  score double precision not null,
  reason text not null,
  unique (run_on, item_id)
);

create index if not exists daily_picks_run_on_idx on daily_picks (run_on desc, rank);

create table if not exists digest_runs (
  run_on date primary key,
  sent_at timestamptz not null default now()
);

alter table items enable row level security;
alter table clusters enable row level security;
alter table cluster_items enable row level security;
alter table daily_picks enable row level security;
alter table digest_runs enable row level security;

revoke all on table items, clusters, cluster_items, daily_picks, digest_runs from anon, authenticated;
grant all on table items, clusters, cluster_items, daily_picks, digest_runs to service_role;
