export function hasExtractedBody(text: string | null | undefined): boolean {
  return Boolean((text || "").trim());
}

export function partitionUnfetched<
  T extends { extracted_text?: string | null; ingest_status?: string },
>(items: T[]): { held: T[]; needsText: T[]; saved: T[] } {
  const held: T[] = [];
  const needsText: T[] = [];
  const saved: T[] = [];
  for (const item of items) {
    if (item.ingest_status === "held") {
      held.push(item);
    } else if (hasExtractedBody(item.extracted_text)) {
      saved.push(item);
    } else {
      needsText.push(item);
    }
  }
  return { held, needsText, saved };
}

export function unfetchedDeleteGuard(
  row: { ingest_status: string } | null,
): string | null {
  if (!row || !UNFETCHED_STATUSES.includes(row.ingest_status)) {
    return "Item is not awaiting a body.";
  }
  return null;
}

/** Statuses listed on Unfetched: awaiting text, or held by the tripwire. */
export const UNFETCHED_STATUSES = ["pending_body", "held"];

/** Release sends a held item to the worker's next run, read without the tripwire. */
export function releaseHeldGuard(
  row: { ingest_status: string } | null,
): string | null {
  if (!row || row.ingest_status !== "held") {
    return "Item is not held.";
  }
  return null;
}

export type UnfetchedFillMode = "idle" | "paste" | "pdf";

export function unfetchedIdleActionsDisabled(mode: UnfetchedFillMode): boolean {
  return mode !== "idle";
}
