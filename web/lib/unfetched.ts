export function hasExtractedBody(text: string | null | undefined): boolean {
  return Boolean((text || "").trim());
}

export function partitionUnfetched<T extends { extracted_text?: string | null }>(
  items: T[],
): { needsText: T[]; saved: T[] } {
  const needsText: T[] = [];
  const saved: T[] = [];
  for (const item of items) {
    if (hasExtractedBody(item.extracted_text)) {
      saved.push(item);
    } else {
      needsText.push(item);
    }
  }
  return { needsText, saved };
}

export function unfetchedDeleteGuard(
  row: { ingest_status: string } | null,
): string | null {
  if (!row || row.ingest_status !== "pending_body") {
    return "Item is not awaiting a body.";
  }
  return null;
}
