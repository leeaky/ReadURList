import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  bulkAddTopics,
  bulkRemoveTopics,
  bulkSetSubject,
  canonicalizeLabel,
  changedRows,
  foldLabel,
  parseItemIds,
  parseTargetLabel,
  remapGuard,
  remapSubjects,
  remapTopics,
  withUniqueTopics,
  type OrganizeItem,
} from "./organize.ts";

function row(
  partial: Partial<OrganizeItem> & { id: number },
): OrganizeItem {
  return {
    subject: "",
    topics: [],
    ingest_status: "ready",
    ...partial,
  };
}

describe("foldLabel", () => {
  it("collapses whitespace and maps unicode dashes to ASCII", () => {
    assert.equal(foldLabel("  Claude\u2014Code  "), "Claude-Code");
  });
});

describe("canonicalizeLabel", () => {
  it("keeps an existing spelling on case-insensitive match", () => {
    assert.equal(
      canonicalizeLabel("claude code", ["Claude Code", "MoE"]),
      "Claude Code",
    );
  });

  it("returns the folded new label when nothing matches", () => {
    assert.equal(canonicalizeLabel("  New Bucket  ", ["Claude Code"]), "New Bucket");
  });
});

describe("parseTargetLabel", () => {
  it("rejects a blank label", () => {
    const result = parseTargetLabel("   ");
    assert.equal(result.ok, false);
    if (!result.ok) {
      assert.equal(result.error, "Name is required.");
    }
  });

  it("trims a usable label", () => {
    assert.deepEqual(parseTargetLabel("  Claude Code  "), {
      ok: true,
      label: "Claude Code",
    });
  });
});

describe("remapGuard", () => {
  it("rejects a blank source", () => {
    assert.equal(remapGuard("  ", "Keep"), "Choose a label to merge.");
  });

  it("rejects merging a label into the same folded spelling", () => {
    assert.equal(
      remapGuard("Claude Code", "  Claude   Code  "),
      "Choose a different name.",
    );
  });

  it("allows a case-only rename", () => {
    assert.equal(remapGuard("claude code", "Claude Code"), null);
  });

  it("allows a real merge", () => {
    assert.equal(remapGuard("Claude Code workflow", "Claude Code"), null);
  });
});

describe("remapSubjects", () => {
  it("renames a subject and keeps a case-only spelling change", () => {
    const items = [
      row({ id: 1, subject: "claude code" }),
      row({ id: 2, subject: "MoE" }),
    ];
    const next = remapSubjects(items, "claude code", "Claude Code");
    assert.equal(next[0].subject, "Claude Code");
    assert.equal(next[1].subject, "MoE");
  });

  it("merges into an existing subject spelling", () => {
    const items = [
      row({ id: 1, subject: "Claude Code workflow" }),
      row({ id: 2, subject: "Claude Code" }),
    ];
    const next = remapSubjects(items, "Claude Code workflow", "claude code");
    assert.equal(next[0].subject, "Claude Code");
    assert.equal(next[1].subject, "Claude Code");
  });
});

describe("remapTopics", () => {
  it("replaces a tag and dedupes when the target is already present", () => {
    const items = [
      row({ id: 1, topics: ["cli", "open source"] }),
      row({ id: 2, topics: ["cli"] }),
    ];
    const next = remapTopics(items, "cli", "open source");
    assert.deepEqual(next[0].topics, ["open source"]);
    assert.deepEqual(next[1].topics, ["open source"]);
  });

  it("renames a tag spelling across items", () => {
    const items = [row({ id: 1, topics: ["Large Language Models", "cli"] })];
    const next = remapTopics(items, "Large Language Models", "large language models");
    assert.deepEqual(next[0].topics, ["large language models", "cli"]);
  });
});

describe("withUniqueTopics", () => {
  it("collapses duplicate tags on every item", () => {
    const items = [
      row({ id: 1, topics: ["a", "a", "b"] }),
      row({ id: 2, topics: ["c"] }),
    ];
    assert.deepEqual(withUniqueTopics(items)[0].topics, ["a", "b"]);
    assert.deepEqual(withUniqueTopics(items)[1].topics, ["c"]);
  });
});

describe("bulkSetSubject", () => {
  it("sets subject only on selected ids", () => {
    const items = [
      row({ id: 1, subject: "A" }),
      row({ id: 2, subject: "B" }),
    ];
    const next = bulkSetSubject(items, [2], "Claude Code");
    assert.equal(next[0].subject, "A");
    assert.equal(next[1].subject, "Claude Code");
  });
});

describe("bulkAddTopics", () => {
  it("collapses duplicate tags already on an item", () => {
    const items = [
      row({
        id: 1,
        topics: ["financial markets", "llm", "financial markets"],
      }),
    ];
    const next = bulkAddTopics(items, [1], []);
    assert.deepEqual(next[0].topics, ["financial markets", "llm"]);
  });

  it("adds tags to selected items, dedupes, and caps at 8", () => {
    const items = [
      row({ id: 1, topics: ["cli"] }),
      row({ id: 2, topics: ["a", "b", "c", "d", "e", "f", "g", "h"] }),
    ];
    const next = bulkAddTopics(items, [1, 2], ["CLI", "agents"]);
    assert.deepEqual(next[0].topics, ["cli", "agents"]);
    assert.deepEqual(next[1].topics, ["a", "b", "c", "d", "e", "f", "g", "h"]);
  });
});

describe("bulkRemoveTopics", () => {
  it("removes matching tags case-insensitively from selected items", () => {
    const items = [
      row({ id: 1, topics: ["cli", "ux"] }),
      row({ id: 2, topics: ["CLI"] }),
    ];
    const next = bulkRemoveTopics(items, [1], ["CLI"]);
    assert.deepEqual(next[0].topics, ["ux"]);
    assert.deepEqual(next[1].topics, ["CLI"]);
  });
});

describe("changedRows", () => {
  it("returns only rows whose subject or topics changed", () => {
    const before = [
      row({ id: 1, subject: "A", topics: ["x"] }),
      row({ id: 2, subject: "B", topics: ["y"] }),
    ];
    const after = [
      row({ id: 1, subject: "A", topics: ["x"] }),
      row({ id: 2, subject: "C", topics: ["y"] }),
    ];
    assert.deepEqual(
      changedRows(before, after).map((item) => item.id),
      [2],
    );
  });
});

describe("parseItemIds", () => {
  it("parses unique positive integers", () => {
    assert.deepEqual(parseItemIds("1, 2, 2, 3"), { ok: true, ids: [1, 2, 3] });
  });

  it("rejects an empty selection", () => {
    const result = parseItemIds("  ");
    assert.equal(result.ok, false);
    if (!result.ok) {
      assert.equal(result.error, "Select at least one article.");
    }
  });
});
