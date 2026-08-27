import Link from "next/link";
import { ItemCard, Shell } from "@/components/ui";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function AllPage({
  searchParams,
}: {
  searchParams: Promise<{ filter?: string }>;
}) {
  const { filter } = await searchParams;
  const db = supabaseAdmin();
  let query = db
    .from("items")
    .select(
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id, ingest_status",
    )
    .eq("ingest_status", "ready")
    .order("created_at", { ascending: false });
  if (filter === "unread") {
    query = query.is("read_at", null);
  } else if (filter === "read") {
    query = query.not("read_at", "is", null);
  }
  const { data, error } = await query;
  if (error) {
    throw new Error(error.message);
  }
  const items = (data || []) as ItemRow[];
  return (
    <Shell current="/all">
      <nav className="filter-row" aria-label="Library filters">
        <Link href="/all" aria-current={!filter ? "page" : undefined}>
          All
        </Link>
        <Link href="/all?filter=unread" aria-current={filter === "unread" ? "page" : undefined}>
          Unread
        </Link>
        <Link href="/all?filter=read" aria-current={filter === "read" ? "page" : undefined}>
          Read
        </Link>
      </nav>
      {items.length === 0 ? (
        <p className="empty">Nothing saved yet.</p>
      ) : (
        items.map((item) => <ItemCard key={item.id} item={item} />)
      )}
    </Shell>
  );
}
