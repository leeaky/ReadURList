alter table items
  add column if not exists skipped_at timestamptz;

create index if not exists items_skipped_at_idx on items (skipped_at);
create index if not exists items_queue_idx on items (ingest_status, read_at, skipped_at);
