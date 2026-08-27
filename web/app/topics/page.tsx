import { ItemCard, Shell } from "@/components/ui";
import { TOPICS_BLURB } from "@/lib/ranking-copy";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function TopicsPage() {
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
  const groups = new Map<string, ItemRow[]>();
  for (const item of items) {
    const key = (item.subject || "untagged").trim() || "untagged";
    const list = groups.get(key) || [];
    list.push(item);
    groups.set(key, list);
  }
  const subjects = [...groups.keys()].sort((a, b) => a.localeCompare(b));
  return (
    <Shell current="/topics">
      <p className="empty">{TOPICS_BLURB}</p>
      {subjects.length === 0 ? (
        <p className="empty">Nothing saved yet.</p>
      ) : (
        subjects.map((subject) => (
          <section className="subject-block" key={subject}>
            <h2>{subject}</h2>
            {(groups.get(subject) || []).map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </section>
        ))
      )}
    </Shell>
  );
}
