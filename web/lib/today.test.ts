import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  fallenOffWords,
  pointsLine,
  readingTime,
  reasonWords,
  splitSections,
} from "./today.ts";

describe("Today pick details", () => {
  it("gives reading time at 230 words a minute, at least 1 minute", () => {
    assert.equal(readingTime(2300), "10 min read");
    assert.equal(readingTime(50), "1 min read");
    assert.equal(readingTime(null), null);
  });

  it("keeps the reason's words and drops the points in brackets", () => {
    assert.equal(
      reasonWords("You keep saving Programming: 5 unread (subject 65 + recency 34 = 99)"),
      "You keep saving Programming: 5 unread",
    );
    assert.equal(reasonWords("Saved today (subject 20 + recency 35 = 55)"), "Saved today");
    assert.equal(reasonWords("Plain reason"), "Plain reason");
  });

  it("shows the two parts and their total", () => {
    assert.equal(pointsLine(65, 34), "subject 65 + recency 34 = 99 points");
    assert.equal(pointsLine(null, 34), null);
  });

  it("splits picks into short and long, missing section counting as short", () => {
    const picks = [
      { rank: 1, section: "short" },
      { rank: 2, section: null },
      { rank: 4, section: "long" },
    ];
    const { short, long } = splitSections(picks);
    assert.deepEqual(short.map((p) => p.rank), [1, 2]);
    assert.deepEqual(long.map((p) => p.rank), [4]);
  });
});

describe("Fallen off", () => {
  it("names the cause in words and the points before and after", () => {
    assert.deepEqual(
      fallenOffWords({ cause: "outscored", points_before: 74, points_after: 72 }),
      { cause: "outscored by newer saves", points: "74 → 72 points" },
    );
    assert.deepEqual(
      fallenOffWords({ cause: "subject_full", points_before: 60, points_after: 58 }),
      { cause: "its subject already has two picks", points: "60 → 58 points" },
    );
  });

  it("shows only the points before when the link is no longer scored", () => {
    assert.deepEqual(
      fallenOffWords({ cause: "read", points_before: 99, points_after: null }),
      { cause: "you read it", points: "was 99 points" },
    );
    assert.equal(
      fallenOffWords({ cause: "skipped", points_before: 50, points_after: null }).cause,
      "you skipped it",
    );
    assert.equal(
      fallenOffWords({ cause: "gone", points_before: 50, points_after: null }).cause,
      "no longer in the pile",
    );
  });
});
