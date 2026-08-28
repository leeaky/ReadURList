import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  RANKING_TODAY_BLURB,
  TOPICS_BLURB,
  UNREAD_BLURB,
} from "./ranking-copy.ts";

describe("ranking copy", () => {
  it("explains Today ranking without scores or clusters", () => {
    assert.match(RANKING_TODAY_BLURB, /five unread ready pieces/i);
    assert.match(RANKING_TODAY_BLURB, /subject you keep saving/i);
    assert.match(RANKING_TODAY_BLURB, /recency/i);
    assert.match(RANKING_TODAY_BLURB, /reading path/i);
    assert.match(RANKING_TODAY_BLURB, /source priority/i);
    assert.doesNotMatch(RANKING_TODAY_BLURB, /0\.45|score/i);
    assert.doesNotMatch(RANKING_TODAY_BLURB, /cluster/i);
  });

  it("ties Topics and Unread to ranking", () => {
    assert.match(TOPICS_BLURB, /subject/i);
    assert.match(UNREAD_BLURB, /Today/i);
  });
});
