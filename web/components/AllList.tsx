"use client";

import Link from "next/link";
import { ItemCard } from "./ItemCard";
import { useFilters } from "./AppFrame";
import { allHref, effortLabel, matchesLength, type Length } from "@/lib/effort";
import { filterItems, type FilterStatus } from "@/lib/filters";
import type { ItemRow } from "@/lib/supabase";

const STATUS_LINKS: { status: FilterStatus; label: string }[] = [
  { status: null, label: "All" },
  { status: "unread", label: "Unread" },
  { status: "stale", label: "Stale 14+" },
  { status: "read", label: "Read" },
  { status: "skipped", label: "Skipped" },
];

const LENGTH_LINKS: { length: Length | null; label: string }[] = [
  { length: null, label: "Any length" },
  { length: "short", label: "Short" },
  { length: "long", label: "Long" },
];

function statusLabel(status: FilterStatus): string {
  if (status === "unread") return "Unread";
  if (status === "read") return "Read";
  if (status === "skipped") return "Skipped";
  if (status === "stale") return "Stale 14+";
  return "";
}

export function AllList({
  items,
  subjects,
  length,
}: {
  items: ItemRow[];
  subjects: string[];
  length: Length | null;
}) {
  const filters = useFilters();
  const visible = filterItems(items, filters).filter((item) => matchesLength(item, length));

  return (
    <>
      <div className="page-heading">
        <h1 className="page-title">All</h1>
        <div className="page-heading-meta">
          <span className="article-count text-muted">
            {visible.length} articles
            {filters.status ? ` · ${statusLabel(filters.status)}` : ""}
            {length ? ` · ${length === "short" ? "Short" : "Long"}` : ""}
          </span>
          <Link href="/organize" className="btn btn-secondary">
            Organize
          </Link>
        </div>
      </div>
      <div className="status-chips" aria-label="Library filters">
        {STATUS_LINKS.map((link) => (
          <Link
            key={link.label}
            href={allHref(link.status, length)}
            className={filters.status === link.status ? "tag tag-accent" : "tag tag-outline"}
            aria-current={filters.status === link.status ? "page" : undefined}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <div className="status-chips" aria-label="Length filter">
        {LENGTH_LINKS.map((link) => (
          <Link
            key={link.label}
            href={allHref(filters.status ?? null, link.length)}
            className={length === link.length ? "tag tag-accent" : "tag tag-outline"}
            aria-current={length === link.length ? "true" : undefined}
          >
            {link.label}
          </Link>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="empty">No articles match your filters.</p>
      ) : (
        <div className="article-list article-list--all">
          {visible.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              readTime={effortLabel(item.word_count)}
              subjects={subjects}
            />
          ))}
        </div>
      )}
    </>
  );
}
