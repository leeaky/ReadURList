import { AppFrame } from "@/components/AppFrame";
import { TodayList } from "@/components/TodayList";
import { isReadyItem } from "@/lib/item-edit";
import { subjectsFromItems } from "@/lib/filters";
import { RANKING_TODAY_BLURB } from "@/lib/ranking-copy";
import { supabaseAdmin, type DailyPickRow, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

function asItem(value: DailyPickRow["items"]): ItemRow | null {
  if (!value) return null;
  return Array.isArray(value) ? value[0] ?? null : value;
}

export default async function TodayPage() {
  const db = supabaseAdmin();
  const latestPromise = db
    .from("daily_picks")
    .select("run_on")
    .order("run_on", { ascending: false })
    .limit(1)
    .maybeSingle();
  const readyPromise = db
    .from("items")
    .select("subject, topics")
    .eq("ingest_status", "ready");
  const [latest, ready] = await Promise.all([latestPromise, readyPromise]);
  if (ready.error) {
    throw new Error(ready.error.message);
  }
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
        if (!item || !isReadyItem(item)) {
          return null;
        }
        return { item, reason: row.reason, rank: row.rank };
      })
      .filter((row): row is { item: ItemRow; reason: string; rank: number } => row !== null);
  }

  const facetItems = (ready.data || []) as Array<{ subject: string; topics: string[] | null }>;
  const subjects = subjectsFromItems(facetItems).map((row) => row.name);

  return (
    <AppFrame current="/" showSidebar facetItems={facetItems}>
      <h1 className="page-title">Today</h1>
      <p className="page-blurb text-muted">{RANKING_TODAY_BLURB}</p>
      <TodayList picks={picks} subjects={subjects} />
    </AppFrame>
  );
}
