import { ItemCard, Shell } from "@/components/ui";
import { supabaseAdmin, type DailyPickRow, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

function asItem(value: DailyPickRow["items"]): ItemRow | null {
  if (!value) return null;
  return Array.isArray(value) ? value[0] ?? null : value;
}

export default async function TodayPage() {
  const db = supabaseAdmin();
  const latest = await db
    .from("daily_picks")
    .select("run_on")
    .order("run_on", { ascending: false })
    .limit(1)
    .maybeSingle();
  const runOn = latest.data?.run_on;
  let picks: { item: ItemRow; reason: string; rank: number }[] = [];
  if (runOn) {
    const { data, error } = await db
      .from("daily_picks")
      .select("run_on, item_id, rank, score, reason, items(*)")
      .eq("run_on", runOn)
      .order("rank");
    if (error) {
      throw new Error(error.message);
    }
    picks = ((data || []) as DailyPickRow[])
      .map((row) => {
        const item = asItem(row.items);
        return item ? { item, reason: row.reason, rank: row.rank } : null;
      })
      .filter((row): row is { item: ItemRow; reason: string; rank: number } => row !== null);
  }

  const path = await db
    .from("items")
    .select(
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id",
    )
    .not("read_at", "is", null)
    .order("read_at", { ascending: false })
    .limit(10);

  return (
    <Shell current="/">
      <h2 className="section-title">Today</h2>
      {picks.length === 0 ? (
        <p className="empty">No ranked picks yet. Run the daily job on the NUC (`second-read-digest` or /digest).</p>
      ) : (
        picks.map((p) => <ItemCard key={p.item.id} item={p.item} reason={p.reason} />)
      )}
      <h2 className="section-title">Path</h2>
      {(path.data || []).length === 0 ? (
        <p className="empty">Nothing marked read yet.</p>
      ) : (
        (path.data as ItemRow[]).map((item) => <ItemCard key={item.id} item={item} />)
      )}
    </Shell>
  );
}
