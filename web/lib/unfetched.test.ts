import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  hasExtractedBody,
  partitionUnfetched,
  unfetchedDeleteGuard,
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
});

describe("unfetchedDeleteGuard", () => {
  it("allows pending_body", () => {
    assert.equal(unfetchedDeleteGuard({ ingest_status: "pending_body" }), null);
  });

  it("refuses missing rows and ready items", () => {
    assert.equal(unfetchedDeleteGuard(null), "Item is not awaiting a body.");
    assert.equal(
      unfetchedDeleteGuard({ ingest_status: "ready" }),
      "Item is not awaiting a body.",
    );
  });
});
