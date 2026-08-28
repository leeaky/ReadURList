"use client";

import { UnfetchedCard } from "./UnfetchedCard";
import { useFilters } from "./AppFrame";
import { filterItems } from "@/lib/filters";
import { partitionUnfetched } from "@/lib/unfetched";
import type { ItemRow } from "@/lib/supabase";

function Section({
  title,
  items,
  muted,
}: {
  title: string;
  items: ItemRow[];
  muted?: boolean;
}) {
  if (items.length === 0) {
    return null;
  }
  return (
    <section className={muted ? "unfetched-section is-muted" : "unfetched-section"}>
      <h2 className={muted ? "section-title is-muted" : "section-title"}>{title}</h2>
      <div className="article-list">
        {items.map((item) => (
          <UnfetchedCard key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}

export function UnfetchedList({ items }: { items: ItemRow[] }) {
  const filters = useFilters();
  const visible = filterItems(items, { ...filters, matchUrl: true });
  const { needsText, saved } = partitionUnfetched(visible);

  if (items.length === 0) {
    return <p className="empty">No items waiting for article text.</p>;
  }
  if (visible.length === 0) {
    return <p className="empty">No articles match your filters.</p>;
  }
  return (
    <>
      <Section title="Needs article text" items={needsText} />
      <Section title="Saved for today’s fill-in" items={saved} muted />
    </>
  );
}
