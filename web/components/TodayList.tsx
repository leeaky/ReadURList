"use client";

import { ItemCard } from "./ItemCard";
import { useFilters } from "./AppFrame";
import { itemMatchesFilter } from "@/lib/filters";
import type { ItemRow } from "@/lib/supabase";

export function TodayList({
  picks,
  subjects,
}: {
  picks: { item: ItemRow; reason: string; rank: number }[];
  subjects: string[];
}) {
  const filters = useFilters();
  const visible = picks.filter((pick) => itemMatchesFilter(pick.item, filters));

  if (picks.length === 0) {
    return (
      <p className="empty">
        No ranked picks yet. Run the daily job on the NUC (`second-read-digest` or /digest).
      </p>
    );
  }
  if (visible.length === 0) {
    return <p className="empty">No articles match your filters.</p>;
  }
  return (
    <div className="article-list">
      {visible.map((pick) => (
        <ItemCard
          key={pick.item.id}
          item={pick.item}
          reason={pick.reason}
          rank={pick.rank}
          subjects={subjects}
        />
      ))}
    </div>
  );
}
