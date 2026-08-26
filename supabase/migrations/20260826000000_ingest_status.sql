alter table items
  add column if not exists ingest_status varchar(32) not null default 'ready';

create index if not exists items_ingest_status_idx on items (ingest_status);
