export type OrganizeItem = {
  id: number;
  subject: string;
  topics: string[];
  ingest_status?: string;
};

const DASHES = /[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d]/g;
const WS = /\s+/g;

export function foldLabel(raw: string): string {
  return (raw || "").replace(DASHES, "-").replace(WS, " ").trim();
}

export function canonicalizeLabel(raw: string, existing: string[]): string {
  const folded = foldLabel(raw);
  if (!folded) {
    return "";
  }
  const key = folded.toLowerCase();
  for (const item of existing) {
    if (foldLabel(item).toLowerCase() === key) {
      return item.trim();
    }
  }
  return folded;
}

export type LabelParseResult =
  | { ok: true; label: string }
  | { ok: false; error: string };

export function parseTargetLabel(raw: string): LabelParseResult {
  const label = foldLabel(raw);
  if (!label) {
    return { ok: false, error: "Name is required." };
  }
  return { ok: true, label };
}

export function remapGuard(from: string, to: string): string | null {
  const source = foldLabel(from);
  const target = foldLabel(to);
  if (!source) {
    return "Choose a label to merge.";
  }
  if (!target) {
    return "Name is required.";
  }
  if (source === target) {
    return "Choose a different name.";
  }
  return null;
}

function subjectKey(item: OrganizeItem): string {
  return foldLabel(item.subject).toLowerCase();
}

function topicKey(tag: string): string {
  return foldLabel(tag).toLowerCase();
}

function existingSubjectsExcept(items: OrganizeItem[], from: string): string[] {
  const skip = foldLabel(from).toLowerCase();
  return items
    .map((item) => item.subject)
    .filter((subject) => foldLabel(subject).toLowerCase() !== skip);
}

function existingTopicsExcept(items: OrganizeItem[], from: string): string[] {
  const skip = foldLabel(from).toLowerCase();
  const out: string[] = [];
  for (const item of items) {
    for (const tag of item.topics) {
      if (foldLabel(tag).toLowerCase() !== skip) {
        out.push(tag);
      }
    }
  }
  return out;
}

export function remapSubjects(
  items: OrganizeItem[],
  from: string,
  to: string,
): OrganizeItem[] {
  const fromKey = foldLabel(from).toLowerCase();
  const target = canonicalizeLabel(to, existingSubjectsExcept(items, from));
  return items.map((item) =>
    subjectKey(item) === fromKey ? { ...item, subject: target } : item,
  );
}

function replaceTopics(topics: string[], fromKey: string, target: string): string[] {
  const next: string[] = [];
  const seen = new Set<string>();
  for (const tag of topics) {
    const replaced = topicKey(tag) === fromKey ? target : tag;
    const key = topicKey(replaced);
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    next.push(replaced);
  }
  return next;
}

export function remapTopics(
  items: OrganizeItem[],
  from: string,
  to: string,
): OrganizeItem[] {
  const fromKey = foldLabel(from).toLowerCase();
  const target = canonicalizeLabel(to, existingTopicsExcept(items, from));
  return items.map((item) => ({
    ...item,
    topics: replaceTopics(item.topics, fromKey, target),
  }));
}

export function bulkSetSubject(
  items: OrganizeItem[],
  ids: number[],
  subject: string,
): OrganizeItem[] {
  const selected = new Set(ids);
  const target = canonicalizeLabel(
    subject,
    items.map((item) => item.subject),
  );
  return items.map((item) =>
    selected.has(item.id) ? { ...item, subject: target } : item,
  );
}

export function bulkAddTopics(
  items: OrganizeItem[],
  ids: number[],
  tags: string[],
): OrganizeItem[] {
  const selected = new Set(ids);
  return items.map((item) => {
    if (!selected.has(item.id)) {
      return item;
    }
    const seen = new Set<string>();
    const next: string[] = [];
    for (const tag of [...item.topics, ...tags]) {
      const name = (tag || "").trim();
      if (!name) {
        continue;
      }
      const key = name.toLowerCase();
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      next.push(name);
      if (next.length >= 8) {
        break;
      }
    }
    return { ...item, topics: next };
  });
}

export function bulkRemoveTopics(
  items: OrganizeItem[],
  ids: number[],
  tags: string[],
): OrganizeItem[] {
  const selected = new Set(ids);
  const remove = new Set(
    tags.map((tag) => topicKey(tag)).filter((key) => key.length > 0),
  );
  return items.map((item) => {
    if (!selected.has(item.id)) {
      return item;
    }
    return {
      ...item,
      topics: item.topics.filter((tag) => !remove.has(topicKey(tag))),
    };
  });
}

function topicsEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) {
    return false;
  }
  return a.every((tag, index) => tag === b[index]);
}

export function changedRows(
  before: OrganizeItem[],
  after: OrganizeItem[],
): OrganizeItem[] {
  const prev = new Map(before.map((item) => [item.id, item]));
  return after.filter((item) => {
    const original = prev.get(item.id);
    if (!original) {
      return true;
    }
    return (
      original.subject !== item.subject ||
      !topicsEqual(original.topics, item.topics)
    );
  });
}

export type ItemIdsResult =
  | { ok: true; ids: number[] }
  | { ok: false; error: string };

export function parseItemIds(raw: unknown): ItemIdsResult {
  const ids: number[] = [];
  const seen = new Set<number>();
  for (const part of String(raw ?? "").split(/[,\s]+/)) {
    if (!part) {
      continue;
    }
    const id = Number(part);
    if (!Number.isInteger(id) || id <= 0) {
      return { ok: false, error: "Invalid article." };
    }
    if (!seen.has(id)) {
      seen.add(id);
      ids.push(id);
    }
  }
  if (ids.length === 0) {
    return { ok: false, error: "Select at least one article." };
  }
  return { ok: true, ids };
}
