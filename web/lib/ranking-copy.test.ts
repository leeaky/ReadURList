import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  CLUSTERS_BLURB,
  RANKING_TODAY_BLURB,
  TOPICS_BLURB,
  UNREAD_BLURB,
} from "./ranking-copy.ts";

describe("ranking copy", () => {
  it("explains Today ranking without mentioning scores", () => {
    assert.match(RANKING_TODAY_BLURB, /five unread ready pieces/i);
    assert.match(RANKING_TODAY_BLURB, /subject you keep saving/i);
    assert.doesNotMatch(RANKING_TODAY_BLURB, /0\.35|score/i);
  });

  it("ties Topics, Clusters, and Unread to ranking", () => {
    assert.match(TOPICS_BLURB, /subject/i);
    assert.match(CLUSTERS_BLURB, /subject\/topics/i);
    assert.match(UNREAD_BLURB, /Today/i);
  });
});
