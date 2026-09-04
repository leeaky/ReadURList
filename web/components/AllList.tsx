"use client";

import Link from "next/link";
import { ItemCard } from "./ItemCard";
import { useFilters } from "./AppFrame";
import { filterItems, type FilterStatus } from "@/lib/filters";
import type { ItemRow } from "@/lib/supabase";

const STATUS_LINKS: { href: string; status: FilterStatus; label: string }[] = [
  { href: "/all", status: null, label: "All" },
  { href: "/all?status=unread", status: "unread", label: "Unread" },
  { href: "/all?status=stale", status: "stale", label: "Stale 14+" },
  { href: "/all?status=read", status: "read", label: "Read" },
  { href: "/all?status=skipped", status: "skipped", label: "Skipped" },
];

function statusLabel(status: FilterStatus): string {
  if (status === "unread") return "Unread";
  if (status === "read") return "Read";
  if (status === "skipped") return "Skipped";
  if (status === "stale") return "Stale 14+";
  return "";
}

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
            {filters.status ? ` · ${statusLabel(filters.status)}` : ""}
          </span>
          <Link href="/organize" className="btn btn-secondary">
            Organize
          </Link>
        </div>
      </div>
      <div className="status-chips" aria-label="Library filters">
        {STATUS_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={filters.status === link.status ? "tag tag-accent" : "tag tag-outline"}
            aria-current={filters.status === link.status ? "page" : undefined}
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
            <ItemCard key={item.id} item={item} subjects={subjects} />
          ))}
        </div>
      )}
    </>
  );
}
