export type FilterableItem = {
  title: string;
  snapshot: string;
  subject: string;
  topics: string[] | null;
  url?: string;
  read_at?: string | null;
};

export type FilterStatus = "unread" | "read" | null;

export type FilterState = {
  search: string;
  selectedSubjects: string[];
  selectedTags: string[];
  status?: FilterStatus;
  matchUrl?: boolean;
};

export function itemMatchesFilter(item: FilterableItem, state: FilterState): boolean {
  const q = state.search.trim().toLowerCase();
  if (q) {
    const hay = [
      item.title,
      item.snapshot,
      ...(item.topics ?? []),
      ...(state.matchUrl ? [item.url ?? ""] : []),
    ]
      .join("\n")
      .toLowerCase();
    if (!hay.includes(q)) {
      return false;
    }
  }

  if (state.selectedSubjects.length > 0 && !state.selectedSubjects.includes(item.subject)) {
    return false;
  }

  if (state.selectedTags.length > 0) {
    const topics = item.topics ?? [];
    if (!state.selectedTags.some((tag) => topics.includes(tag))) {
      return false;
    }
  }

  if (state.status === "unread" && item.read_at) {
    return false;
  }
  if (state.status === "read" && !item.read_at) {
    return false;
  }

  return true;
}

export function filterItems<T extends FilterableItem>(items: T[], state: FilterState): T[] {
  return items.filter((item) => itemMatchesFilter(item, state));
}

export function subjectsFromItems(
  items: Array<{ subject: string }>,
): { name: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    const name = item.subject.trim();
    if (!name) continue;
    counts.set(name, (counts.get(name) || 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

export function uniqueTopics(topics: string[] | null): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const tag of topics ?? []) {
    const name = tag.trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(name);
  }
  return out;
}

export function tagsFromItems(
  items: Array<{ topics: string[] | null }>,
  limit?: number,
): { tag: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    for (const tag of uniqueTopics(item.topics)) {
      counts.set(tag, (counts.get(tag) || 0) + 1);
    }
  }
  const sorted = [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
  return limit == null ? sorted : sorted.slice(0, limit);
}

export function facetItemsFromPicks<T extends { subject: string; topics: string[] | null }>(
  picks: Array<{ item: T }>,
): T[] {
  return picks.map((pick) => pick.item);
}

export function itemsMatchingSubjects<T extends { subject: string }>(
  items: T[],
  selectedSubjects: string[],
): T[] {
  if (selectedSubjects.length === 0) {
    return items;
  }
  return items.filter((item) => selectedSubjects.includes(item.subject));
}

export function tagsInSelectedSubjects(
  items: Array<{ subject: string; topics: string[] | null }>,
  selectedSubjects: string[],
): { tag: string; count: number }[] {
  return tagsFromItems(itemsMatchingSubjects(items, selectedSubjects));
}
