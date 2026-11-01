// Is it working? (build map stage 10) — same counts as the worker's
// src/readurlist/rank/week.py, over the last 7 days.

export type WeekStats = {
  shown: number;
  read: number;
  skipped: number;
  pileThen: number;
  pileNow: number;
};

type Dated = { read_at?: string | null; skipped_at?: string | null };

function before(value: string | null | undefined, since: Date): boolean {
  return value != null && new Date(value).getTime() < since.getTime();
}

export function weekStats(
  picks: (Dated & { item_id: number })[],
  readyItems: (Dated & { created_at?: string | null })[],
  since: Date,
): WeekStats {
  const shown = new Map<number, Dated>();
  for (const pick of picks) shown.set(pick.item_id, pick);
  const rows = [...shown.values()];
  return {
    shown: rows.length,
    read: rows.filter((r) => r.read_at).length,
    skipped: rows.filter((r) => !r.read_at && r.skipped_at).length,
    pileThen: readyItems.filter(
      (i) =>
        before(i.created_at, since) && !before(i.read_at, since) && !before(i.skipped_at, since),
    ).length,
    pileNow: readyItems.filter((i) => !i.read_at && !i.skipped_at).length,
  };
}

export function weekLine(stats: WeekStats, label: string): string {
  const pile = `Unread pile ${stats.pileThen} → ${stats.pileNow}.`;
  if (stats.shown === 0) return `${label}: no picks shown. ${pile}`;
  const rate = Math.round((100 * stats.read) / stats.shown);
  const verdict = stats.read * 2 >= stats.shown ? "working" : "below half: tune the ranking";
  return `${label}: read ${stats.read} of ${stats.shown} picks (${rate}%, ${verdict}). Skipped ${stats.skipped}. ${pile}`;
}
