"use client";

import { UnfetchedCard } from "./UnfetchedCard";
import { useFilters } from "./AppFrame";
import { filterItems } from "@/lib/filters";
import type { ItemRow } from "@/lib/supabase";

export function UnfetchedList({ items }: { items: ItemRow[] }) {
  const filters = useFilters();
  const visible = filterItems(items, { ...filters, matchUrl: true });

  if (items.length === 0) {
    return <p className="empty">No items waiting for article text.</p>;
  }
  if (visible.length === 0) {
    return <p className="empty">No articles match your filters.</p>;
  }
  return (
    <div className="unfetched-list">
      {visible.map((item) => (
        <UnfetchedCard key={item.id} item={item} />
      ))}
    </div>
  );
}
