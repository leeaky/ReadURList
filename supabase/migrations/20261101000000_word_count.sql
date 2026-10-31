-- Stage 4: effort label. Words in the stored text; the label (short/long) and
-- reading time (230 words a minute) are derived from it. Additive: code
-- already live ignores the column. Older items get it from
-- `readurlist-effort-backfill`.
alter table items
  add column if not exists word_count integer;
