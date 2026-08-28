import { AppFrame } from "@/components/AppFrame";
import { OrganizeView } from "@/components/OrganizeView";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function OrganizePage() {
  const db = supabaseAdmin();
  const { data, error } = await db
    .from("items")
    .select(
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id, ingest_status",
    )
    .eq("ingest_status", "ready")
    .order("created_at", { ascending: false });
  if (error) {
    throw new Error(error.message);
  }
  const items = (data || []) as ItemRow[];
  return (
    <AppFrame current="/organize" showSidebar={false} facetItems={items}>
      <OrganizeView items={items} />
    </AppFrame>
  );
}
