import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { READY_CORPUS_SELECT } from "./corpus.ts";
import { allHref, effortLabel, effortOf, lengthFromParam, matchesLength } from "./effort.ts";

describe("effort label", () => {
  it("is short under 15 minutes at 230 words a minute, long from 15", () => {
    assert.equal(effortOf(3449), "short");
    assert.equal(effortOf(3450), "long");
    assert.equal(effortOf(null), null);
  });

  it("reads like 'Short · 4 min'", () => {
    assert.equal(effortLabel(920), "Short · 4 min");
    assert.equal(effortLabel(4830), "Long · 21 min");
    assert.equal(effortLabel(10), "Short · 1 min");
    assert.equal(effortLabel(null), null);
  });

  it("All loads each item's word count", () => {
    assert.match(READY_CORPUS_SELECT, /\bword_count\b/);
  });
});

describe("length filter", () => {
  it("keeps everything when no length is chosen", () => {
    assert.equal(matchesLength({ word_count: 5000 }, null), true);
    assert.equal(matchesLength({ word_count: null }, null), true);
  });

  it("matches short or long; no word count counts as short, as in ranking", () => {
    assert.equal(matchesLength({ word_count: 100 }, "short"), true);
    assert.equal(matchesLength({ word_count: 100 }, "long"), false);
    assert.equal(matchesLength({ word_count: 5000 }, "long"), true);
    assert.equal(matchesLength({ word_count: null }, "short"), true);
    assert.equal(matchesLength({}, "long"), false);
  });

  it("reads the length from the address and ignores anything else", () => {
    assert.equal(lengthFromParam("short"), "short");
    assert.equal(lengthFromParam("long"), "long");
    assert.equal(lengthFromParam("medium"), null);
    assert.equal(lengthFromParam(undefined), null);
  });

  it("builds chip links that keep the other filter", () => {
    assert.equal(allHref(null, null), "/all");
    assert.equal(allHref("unread", null), "/all?status=unread");
    assert.equal(allHref(null, "long"), "/all?length=long");
    assert.equal(allHref("unread", "long"), "/all?status=unread&length=long");
  });
});
