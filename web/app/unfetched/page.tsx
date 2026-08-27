import { UnfetchedCard } from "@/components/UnfetchedCard";
import { Shell } from "@/components/ui";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";
import { partitionUnfetched } from "@/lib/unfetched";

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
  const { needsText, saved } = partitionUnfetched(items);

  return (
    <Shell current="/unfetched">
      <h2 className="section-title">Unfetched</h2>
      {items.length === 0 ? (
        <p className="empty">No items waiting for article text.</p>
      ) : (
        <>
          {needsText.length > 0 ? (
            <section>
              <h3 className="section-title">Needs article text</h3>
              {needsText.map((item) => (
                <UnfetchedCard key={item.id} item={item} />
              ))}
            </section>
          ) : null}
          {saved.length > 0 ? (
            <section>
              <h3 className="section-title">Saved for today’s fill-in</h3>
              {saved.map((item) => (
                <UnfetchedCard key={item.id} item={item} />
              ))}
            </section>
          ) : null}
        </>
      )}
    </Shell>
  );
}
