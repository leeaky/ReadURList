import Link from "next/link";
import { ItemCard, Shell } from "@/components/ui";
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
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id",
    )
    .is("read_at", null)
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
      <p className="filter-row">
        <Link href="/unread">All unread</Link>
        {" · "}
        <Link href="/unread?stale=1">Stale (14+ days)</Link>
      </p>
      {items.length === 0 ? (
        <p className="empty">No unread items.</p>
      ) : (
        items.map((item) => <ItemCard key={item.id} item={item} />)
      )}
    </Shell>
  );
}
