import { UnfetchedCard } from "@/components/UnfetchedCard";
import { Shell } from "@/components/ui";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function UnfetchedPage() {
  const db = supabaseAdmin();
  const { data, error } = await db
    .from("items")
    .select(
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id, ingest_status, extracted_text, note",
    )
    .eq("ingest_status", "pending_body")
    .order("created_at", { ascending: false });
  if (error) {
    throw new Error(error.message);
  }
  const items = (data || []) as ItemRow[];

  return (
    <Shell current="/unfetched">
      <h2 className="section-title">Unfetched</h2>
      {items.length === 0 ? (
        <p className="empty">No items waiting for article text.</p>
      ) : (
        items.map((item) => <UnfetchedCard key={item.id} item={item} />)
      )}
    </Shell>
  );
}
