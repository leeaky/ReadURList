import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  hasExtractedBody,
  partitionUnfetched,
  releaseHeldGuard,
  unfetchedDeleteGuard,
  unfetchedIdleActionsDisabled,
} from "./unfetched.ts";

describe("hasExtractedBody", () => {
  it("is false for empty, whitespace, null, and undefined", () => {
    assert.equal(hasExtractedBody(""), false);
    assert.equal(hasExtractedBody("   "), false);
    assert.equal(hasExtractedBody(null), false);
    assert.equal(hasExtractedBody(undefined), false);
  });

  it("is true when trimmed text is non-empty", () => {
    assert.equal(hasExtractedBody("hello"), true);
    assert.equal(hasExtractedBody("  hello  "), true);
  });
});

describe("partitionUnfetched", () => {
  it("splits needs-text vs saved and preserves order", () => {
    const items = [
      { id: 1, extracted_text: "" },
      { id: 2, extracted_text: "body" },
      { id: 3, extracted_text: "  " },
      { id: 4, extracted_text: "more" },
    ];
    const { needsText, saved } = partitionUnfetched(items);
    assert.deepEqual(
      needsText.map((i) => i.id),
      [1, 3],
    );
    assert.deepEqual(
      saved.map((i) => i.id),
      [2, 4],
    );
  });

  it("puts held items in their own group even though they have text", () => {
    const items = [
      { id: 1, extracted_text: "", ingest_status: "pending_body" },
      { id: 2, extracted_text: "page text", ingest_status: "held" },
      { id: 3, extracted_text: "pasted", ingest_status: "pending_body" },
    ];
    const { held, needsText, saved } = partitionUnfetched(items);
    assert.deepEqual(held.map((i) => i.id), [2]);
    assert.deepEqual(needsText.map((i) => i.id), [1]);
    assert.deepEqual(saved.map((i) => i.id), [3]);
  });
});

describe("unfetchedIdleActionsDisabled", () => {
  it("is false while the card is idle so Paste, Attach, and Delete stay usable", () => {
    assert.equal(unfetchedIdleActionsDisabled("idle"), false);
  });

  it("is true after Paste text or Attach PDF expands the fill-in form", () => {
    assert.equal(unfetchedIdleActionsDisabled("paste"), true);
    assert.equal(unfetchedIdleActionsDisabled("pdf"), true);
  });
});

describe("unfetchedDeleteGuard", () => {
  it("allows pending_body", () => {
    assert.equal(unfetchedDeleteGuard({ ingest_status: "pending_body" }), null);
  });

  it("allows held", () => {
    assert.equal(unfetchedDeleteGuard({ ingest_status: "held" }), null);
  });

  it("refuses missing rows and ready items", () => {
    assert.equal(unfetchedDeleteGuard(null), "Item is not awaiting a body.");
    assert.equal(
      unfetchedDeleteGuard({ ingest_status: "ready" }),
      "Item is not awaiting a body.",
    );
  });
});

describe("releaseHeldGuard", () => {
  it("allows held", () => {
    assert.equal(releaseHeldGuard({ ingest_status: "held" }), null);
  });

  it("refuses missing rows and anything not held", () => {
    assert.equal(releaseHeldGuard(null), "Item is not held.");
    assert.equal(releaseHeldGuard({ ingest_status: "pending_body" }), "Item is not held.");
    assert.equal(releaseHeldGuard({ ingest_status: "ready" }), "Item is not held.");
  });
});
