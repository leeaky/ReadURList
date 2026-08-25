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
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id",
    )
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
      <p className="filter-row">
        <Link href="/all">All</Link>
        {" · "}
        <Link href="/all?filter=unread">Unread</Link>
        {" · "}
        <Link href="/all?filter=read">Read</Link>
      </p>
      {items.length === 0 ? (
        <p className="empty">Nothing saved yet.</p>
      ) : (
        items.map((item) => <ItemCard key={item.id} item={item} />)
      )}
    </Shell>
  );
}
