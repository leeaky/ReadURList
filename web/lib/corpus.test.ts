import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  CORPUS_PAGE_SIZE,
  corpusPageRange,
  hasMoreCorpusPages,
} from "./corpus.ts";

describe("corpusPageRange", () => {
  it("uses 1000-row windows so All cannot silently truncate", () => {
    assert.equal(CORPUS_PAGE_SIZE, 1000);
    assert.deepEqual(corpusPageRange(0), { from: 0, to: 999 });
    assert.deepEqual(corpusPageRange(1), { from: 1000, to: 1999 });
  });
});

describe("hasMoreCorpusPages", () => {
  it("fetches another page only when the window is full", () => {
    assert.equal(hasMoreCorpusPages(1000), true);
    assert.equal(hasMoreCorpusPages(999), false);
    assert.equal(hasMoreCorpusPages(0), false);
  });
});
