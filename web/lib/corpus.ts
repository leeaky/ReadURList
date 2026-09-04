export const CORPUS_PAGE_SIZE = 1000;

export const READY_CORPUS_SELECT =
  "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, skipped_at, ingest_status";

export function corpusPageRange(
  pageIndex: number,
  pageSize = CORPUS_PAGE_SIZE,
): { from: number; to: number } {
  const from = pageIndex * pageSize;
  return { from, to: from + pageSize - 1 };
}

export function hasMoreCorpusPages(
  fetchedCount: number,
  pageSize = CORPUS_PAGE_SIZE,
): boolean {
  return fetchedCount >= pageSize;
}
