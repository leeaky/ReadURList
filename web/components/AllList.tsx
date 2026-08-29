"use client";

import Link from "next/link";
import { ItemCard } from "./ItemCard";
import { useFilters } from "./AppFrame";
import { filterItems } from "@/lib/filters";
import type { ItemRow } from "@/lib/supabase";

export function AllList({ items, subjects }: { items: ItemRow[]; subjects: string[] }) {
  const filters = useFilters();
  const visible = filterItems(items, filters);

  return (
    <>
      <div className="page-heading">
        <h1 className="page-title">All</h1>
        <div className="page-heading-meta">
          <span className="article-count text-muted">
            {visible.length} articles
            {filters.status === "unread" ? " · Unread" : filters.status === "read" ? " · Read" : ""}
          </span>
          <Link href="/organize" className="btn btn-secondary">
            Organize
          </Link>
        </div>
      </div>
      {visible.length === 0 ? (
        <p className="empty">No articles match your filters.</p>
      ) : (
        <div className="article-list article-list--all">
          {visible.map((item) => (
            <ItemCard key={item.id} item={item} subjects={subjects} />
          ))}
        </div>
      )}
    </>
  );
}
