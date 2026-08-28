import { AppFrame } from "@/components/AppFrame";
import { UnfetchedList } from "@/components/UnfetchedList";
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
    <AppFrame current="/unfetched" showSidebar={false} facetItems={[]}>
      <h1 className="page-title">Unfetched</h1>
      <p className="page-blurb text-muted">
        Links saved from Telegram. Paste the article text or attach a PDF so it can be summarized.
      </p>
      <UnfetchedList items={items} />
    </AppFrame>
  );
}
