import { AppFrame } from "@/components/AppFrame";
import { TodayList, type FallenOff, type TodayPick } from "@/components/TodayList";
import { isReadyItem } from "@/lib/item-edit";
import { facetItemsFromPicks, subjectsFromItems } from "@/lib/filters";
import { RANKING_TODAY_BLURB } from "@/lib/ranking-copy";
import {
  supabaseAdmin,
  type DailyPickRow,
  type FallenOffRow,
  type ItemRow,
} from "@/lib/supabase";

export const dynamic = "force-dynamic";

function asItem<T>(value: T | T[] | null): T | null {
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
  const waitingPromise = db
    .from("items")
    .select("id", { count: "exact", head: true })
    .eq("ingest_status", "pending_body");
  const [latest, ready, waiting] = await Promise.all([
    latestPromise,
    readyPromise,
    waitingPromise,
  ]);
  if (ready.error) {
    throw new Error(ready.error.message);
  }
  if (waiting.error) {
    throw new Error(waiting.error.message);
  }
  const runOn = latest.data?.run_on;
  let picks: TodayPick[] = [];
  let fallen: FallenOff[] = [];
  if (runOn) {
    const [{ data, error }, fallenRes] = await Promise.all([
      db
        .from("daily_picks")
        .select(
          "run_on, item_id, rank, score, reason, section, subject_points, recency_points, items(*)",
        )
        .eq("run_on", runOn)
        .order("rank"),
      db
        .from("fallen_off")
        .select("item_id, cause, points_before, points_after, items(url, title)")
        .eq("run_on", runOn)
        .order("points_before", { ascending: false }),
    ]);
    if (error) {
      throw new Error(error.message);
    }
    if (fallenRes.error) {
      throw new Error(fallenRes.error.message);
    }
    fallen = ((fallenRes.data || []) as FallenOffRow[]).map((row) => {
      const item = asItem(row.items);
      return {
        itemId: row.item_id,
        url: item?.url ?? "",
        title: item?.title ?? "",
        cause: row.cause,
        pointsBefore: row.points_before,
        pointsAfter: row.points_after,
      };
    });
    picks = ((data || []) as DailyPickRow[])
      .map((row) => {
        const item = asItem<ItemRow>(row.items);
        if (!item || !isReadyItem(item)) {
          return null;
        }
        return {
          item,
          reason: row.reason,
          rank: row.rank,
          section: row.section ?? null,
          subjectPoints: row.subject_points ?? null,
          recencyPoints: row.recency_points ?? null,
        };
      })
      .filter((row): row is TodayPick => row !== null);
  }

  const subjects = subjectsFromItems(
    (ready.data || []) as Array<{ subject: string; topics: string[] | null }>,
  ).map((row) => row.name);

  return (
    <AppFrame current="/" showSidebar facetItems={facetItemsFromPicks(picks)}>
      <h1 className="page-title">Today</h1>
      <p className="page-blurb text-muted">{RANKING_TODAY_BLURB}</p>
      <TodayList
        picks={picks}
        fallen={fallen}
        waitingOnUnfetched={waiting.count ?? 0}
        subjects={subjects}
      />
    </AppFrame>
  );
}
