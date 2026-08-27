import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  itemEditGuard,
  parseItemEdit,
  parseTopicList,
} from "./item-edit.ts";

describe("parseTopicList", () => {
  it("splits on commas, trims, and drops empties", () => {
    assert.deepEqual(parseTopicList("  alpha, beta ,, gamma  "), [
      "alpha",
      "beta",
      "gamma",
    ]);
  });

  it("dedupes case-insensitively and keeps first spelling", () => {
    assert.deepEqual(parseTopicList("OpenReview, openreview, Captcha"), [
      "OpenReview",
      "Captcha",
    ]);
  });

  it("caps at 8 topics", () => {
    const raw = "a,b,c,d,e,f,g,h,i,j";
    assert.deepEqual(parseTopicList(raw), ["a", "b", "c", "d", "e", "f", "g", "h"]);
  });
});

describe("itemEditGuard", () => {
  it("allows ready items", () => {
    assert.equal(itemEditGuard({ ingest_status: "ready" }), null);
  });

  it("refuses missing rows and pending_body stubs", () => {
    assert.equal(itemEditGuard(null), "Item not found.");
    assert.equal(
      itemEditGuard({ ingest_status: "pending_body" }),
      "Only completed articles can be edited.",
    );
  });
});

describe("parseItemEdit", () => {
  it("rejects a blank headline", () => {
    const result = parseItemEdit({
      title: "   ",
      snapshot: "A real abstract.",
      subject: "ML",
      topics: "transformers",
    });
    assert.equal(result.ok, false);
    if (!result.ok) {
      assert.equal(result.error, "Headline is required.");
    }
  });

  it("builds trimmed fields and parsed topics", () => {
    const result = parseItemEdit({
      title: "  Real paper title  ",
      snapshot: "  Two sentence snapshot.  ",
      subject: "  machine learning  ",
      topics: "transformers, openreview",
    });
    assert.deepEqual(result, {
      ok: true,
      fields: {
        title: "Real paper title",
        snapshot: "Two sentence snapshot.",
        subject: "machine learning",
        topics: ["transformers", "openreview"],
      },
    });
  });
});
