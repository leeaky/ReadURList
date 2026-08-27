export type ItemEditFields = {
  title: string;
  snapshot: string;
  subject: string;
  topics: string[];
};

export type ItemEditInput = {
  title: string;
  snapshot: string;
  subject: string;
  topics: string;
};

export type ItemEditResult =
  | { ok: true; fields: ItemEditFields }
  | { ok: false; error: string };

export function parseTopicList(raw: string, cap = 8): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of raw.split(",")) {
    const topic = part.trim();
    if (!topic) continue;
    const key = topic.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(topic);
    if (out.length >= cap) break;
  }
  return out;
}

export function itemEditGuard(
  row: { ingest_status: string } | null,
): string | null {
  if (!row) {
    return "Item not found.";
  }
  if (row.ingest_status !== "ready") {
    return "Only completed articles can be edited.";
  }
  return null;
}

export function parseItemEdit(input: ItemEditInput): ItemEditResult {
  const title = input.title.trim();
  if (!title) {
    return { ok: false, error: "Headline is required." };
  }
  return {
    ok: true,
    fields: {
      title,
      snapshot: input.snapshot.trim(),
      subject: input.subject.trim(),
      topics: parseTopicList(input.topics),
    },
  };
}

export function sendToUnfetchedGuard(
  row: { ingest_status: string } | null,
): string | null {
  if (!row) {
    return "Item not found.";
  }
  if (row.ingest_status !== "ready") {
    return "Only completed articles can be sent to Unfetched.";
  }
  return null;
}

export function sendToUnfetchedFields(): {
  ingest_status: "pending_body";
  extracted_text: "";
  snapshot: "not available";
  subject: "not available";
  topics: string[];
  keywords: string[];
  priority: number;
  note: "Sent back from edit";
} {
  return {
    ingest_status: "pending_body",
    extracted_text: "",
    snapshot: "not available",
    subject: "not available",
    topics: [],
    keywords: [],
    priority: 3,
    note: "Sent back from edit",
  };
}

export function isReadyItem(
  row: { ingest_status?: string } | null,
): boolean {
  return row?.ingest_status === "ready";
}
