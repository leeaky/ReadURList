import Link from "next/link";
import { ItemCard, Shell } from "@/components/ui";
import { UNREAD_BLURB } from "@/lib/ranking-copy";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function UnreadPage({
  searchParams,
}: {
  searchParams: Promise<{ stale?: string }>;
}) {
  const { stale } = await searchParams;
  const db = supabaseAdmin();
  let query = db
    .from("items")
    .select(
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id, ingest_status",
    )
    .is("read_at", null)
    .eq("ingest_status", "ready")
    .order("created_at", { ascending: false });
  if (stale === "1") {
    const cutoff = new Date();
    cutoff.setUTCDate(cutoff.getUTCDate() - 14);
    query = query.lt("created_at", cutoff.toISOString());
  }
  const { data, error } = await query;
  if (error) {
    throw new Error(error.message);
  }
  const items = (data || []) as ItemRow[];
  return (
    <Shell current="/unread">
      <nav className="filter-row" aria-label="Unread filters">
        <Link href="/unread" aria-current={stale === "1" ? undefined : "page"}>
          All unread
        </Link>
        <Link href="/unread?stale=1" aria-current={stale === "1" ? "page" : undefined}>
          Stale (14+ days)
        </Link>
      </nav>
      <p className="empty">{UNREAD_BLURB}</p>
      {items.length === 0 ? (
        <p className="empty">No unread items.</p>
      ) : (
        items.map((item) => <ItemCard key={item.id} item={item} />)
      )}
    </Shell>
  );
}
