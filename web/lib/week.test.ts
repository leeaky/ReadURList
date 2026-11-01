import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { weekLine, weekStats } from "./week.ts";

const SINCE = new Date("2026-10-26T00:00:00Z");
const before = "2026-10-20T09:00:00Z";
const during = "2026-10-28T12:00:00Z";

describe("7-day numbers", () => {
  it("counts distinct picks shown, read and skipped", () => {
    const picks = [
      { item_id: 1, read_at: during, skipped_at: null },
      { item_id: 1, read_at: during, skipped_at: null },
      { item_id: 2, read_at: null, skipped_at: during },
      { item_id: 3, read_at: null, skipped_at: null },
    ];
    const stats = weekStats(picks, [], SINCE);
    assert.deepEqual([stats.shown, stats.read, stats.skipped], [3, 1, 1]);
  });

  it("works out the pile a week ago from dates", () => {
    const items = [
      { created_at: before, read_at: null, skipped_at: null }, // then and now
      { created_at: before, read_at: during, skipped_at: null }, // then only
      { created_at: before, read_at: "2026-10-24T12:00:00Z", skipped_at: null }, // neither
      { created_at: during, read_at: null, skipped_at: null }, // now only
    ];
    const stats = weekStats([], items, SINCE);
    assert.deepEqual([stats.pileThen, stats.pileNow], [2, 2]);
  });
});

describe("7-day line", () => {
  it("gives the read rate and verdict, pile for background", () => {
    assert.equal(
      weekLine({ shown: 12, read: 5, skipped: 3, pileThen: 140, pileNow: 142 }, "Last 7 days"),
      "Last 7 days: read 5 of 12 picks (42%, below half: tune the ranking). Skipped 3. Unread pile 140 → 142.",
    );
    assert.equal(
      weekLine({ shown: 10, read: 5, skipped: 0, pileThen: 9, pileNow: 7 }, "Last 7 days"),
      "Last 7 days: read 5 of 10 picks (50%, working). Skipped 0. Unread pile 9 → 7.",
    );
    assert.equal(
      weekLine({ shown: 0, read: 0, skipped: 0, pileThen: 3, pileNow: 4 }, "Last 7 days"),
      "Last 7 days: no picks shown. Unread pile 3 → 4.",
    );
  });
});
