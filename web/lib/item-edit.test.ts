import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  isReadyItem,
  itemEditGuard,
  parseItemEdit,
  parseTopicList,
  sendToUnfetchedFields,
  sendToUnfetchedGuard,
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

describe("sendToUnfetchedGuard", () => {
  it("allows ready items", () => {
    assert.equal(sendToUnfetchedGuard({ ingest_status: "ready" }), null);
  });

  it("refuses missing rows and non-ready statuses", () => {
    assert.equal(sendToUnfetchedGuard(null), "Item not found.");
    assert.equal(
      sendToUnfetchedGuard({ ingest_status: "pending_body" }),
      "Only completed articles can be sent to Unfetched.",
    );
    assert.equal(
      sendToUnfetchedGuard({ ingest_status: "other" }),
      "Only completed articles can be sent to Unfetched.",
    );
  });
});

describe("sendToUnfetchedFields", () => {
  it("matches the issue #12 stub writes plus the edit note", () => {
    assert.deepEqual(sendToUnfetchedFields(), {
      ingest_status: "pending_body",
      extracted_text: "",
      snapshot: "not available",
      subject: "not available",
      topics: [],
      keywords: [],
      priority: 3,
      note: "Sent back from edit",
    });
  });
});

describe("isReadyItem", () => {
  it("is true only for ready", () => {
    assert.equal(isReadyItem({ ingest_status: "ready" }), true);
    assert.equal(isReadyItem({ ingest_status: "pending_body" }), false);
    assert.equal(isReadyItem({ ingest_status: undefined }), false);
    assert.equal(isReadyItem(null), false);
  });
});
