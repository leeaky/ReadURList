-- Drop V1 leftover columns unused after connect/converse/ping removal.

alter table items drop column if exists summary_one_liner;
alter table items drop column if exists surfaced_count;
