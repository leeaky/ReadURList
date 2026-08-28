import { AppFrame } from "@/components/AppFrame";
import { AllList } from "@/components/AllList";
import { subjectsFromItems, type FilterStatus } from "@/lib/filters";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

function statusFromParams(params: { status?: string; filter?: string }): FilterStatus {
  const value = params.status || params.filter;
  if (value === "unread" || value === "read") {
    return value;
  }
  return null;
}

export default async function AllPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; filter?: string }>;
}) {
  const params = await searchParams;
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
  const subjects = subjectsFromItems(items).map((row) => row.name);
  return (
    <AppFrame
      current="/all"
      showSidebar
      facetItems={items}
      initialStatus={statusFromParams(params)}
    >
      <AllList items={items} subjects={subjects} />
    </AppFrame>
  );
}
