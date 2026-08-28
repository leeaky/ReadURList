import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  filterItems,
  itemMatchesFilter,
  subjectsFromItems,
  tagsFromItems,
  type FilterState,
  type FilterableItem,
} from "./filters.ts";

function item(partial: Partial<FilterableItem> & { title: string }): FilterableItem {
  return {
    snapshot: "",
    subject: "",
    topics: [],
    url: "",
    read_at: null,
    ...partial,
  };
}

const empty: FilterState = {
  search: "",
  selectedSubjects: [],
  selectedTags: [],
  status: null,
};

describe("itemMatchesFilter", () => {
  it("matches search against title, snapshot, and topics, case-insensitive", () => {
    const graph = item({
      title: "Graphify Launch",
      snapshot: "A knowledge graph tool.",
      topics: ["agentic workflows"],
    });
    assert.equal(itemMatchesFilter(graph, { ...empty, search: "graphify" }), true);
    assert.equal(itemMatchesFilter(graph, { ...empty, search: "KNOWLEDGE" }), true);
    assert.equal(itemMatchesFilter(graph, { ...empty, search: "Agentic" }), true);
    assert.equal(itemMatchesFilter(graph, { ...empty, search: "vector" }), false);
  });

  it("matches search against URL when matchUrl is true", () => {
    const row = item({ title: "Stub", url: "https://example.com/graphify-launch" });
    assert.equal(itemMatchesFilter(row, { ...empty, search: "graphify" }), false);
    assert.equal(
      itemMatchesFilter(row, { ...empty, search: "graphify", matchUrl: true }),
      true,
    );
  });

  it("ORs selected subjects and ORs selected tags, ANDs the sets together", () => {
    const a = item({
      title: "A",
      subject: "AI Agents",
      topics: ["claude code", "cli"],
    });
    const b = item({
      title: "B",
      subject: "Developer Tools",
      topics: ["open source"],
    });
    const subjects = { ...empty, selectedSubjects: ["AI Agents", "ML Research"] };
    assert.equal(itemMatchesFilter(a, subjects), true);
    assert.equal(itemMatchesFilter(b, subjects), false);

    const tags = { ...empty, selectedTags: ["cli", "open source"] };
    assert.equal(itemMatchesFilter(a, tags), true);
    assert.equal(itemMatchesFilter(b, tags), true);

    const both = {
      ...empty,
      selectedSubjects: ["AI Agents"],
      selectedTags: ["open source"],
    };
    assert.equal(itemMatchesFilter(a, both), false);
    assert.equal(itemMatchesFilter(b, both), false);
  });

  it("filters unread and read by read_at", () => {
    const unread = item({ title: "U", read_at: null });
    const read = item({ title: "R", read_at: "2026-08-27T00:00:00Z" });
    assert.equal(itemMatchesFilter(unread, { ...empty, status: "unread" }), true);
    assert.equal(itemMatchesFilter(read, { ...empty, status: "unread" }), false);
    assert.equal(itemMatchesFilter(unread, { ...empty, status: "read" }), false);
    assert.equal(itemMatchesFilter(read, { ...empty, status: "read" }), true);
  });
});

describe("filterItems", () => {
  it("returns only matching items in original order", () => {
    const items = [
      item({ title: "Keep", subject: "AI Agents", topics: ["cli"] }),
      item({ title: "Drop", subject: "Startups", topics: ["funding"] }),
      item({ title: "Also", subject: "AI Agents", topics: ["tool use"] }),
    ];
    const out = filterItems(items, { ...empty, selectedSubjects: ["AI Agents"] });
    assert.deepEqual(
      out.map((row) => row.title),
      ["Keep", "Also"],
    );
  });
});

describe("subjectsFromItems", () => {
  it("counts non-empty subjects and sorts by name", () => {
    const items = [
      item({ title: "1", subject: "AI Agents" }),
      item({ title: "2", subject: "Developer Tools" }),
      item({ title: "3", subject: "AI Agents" }),
      item({ title: "4", subject: "  " }),
    ];
    assert.deepEqual(subjectsFromItems(items), [
      { name: "AI Agents", count: 2 },
      { name: "Developer Tools", count: 1 },
    ]);
  });
});

describe("tagsFromItems", () => {
  it("counts topics by frequency, caps at 18, and sorts by count then name", () => {
    const items = [
      item({ title: "1", topics: ["cli", "open source"] }),
      item({ title: "2", topics: ["cli"] }),
      item({ title: "3", topics: ["open source", "ux"] }),
      item({ title: "4", topics: null }),
    ];
    assert.deepEqual(tagsFromItems(items, 2), [
      { tag: "cli", count: 2 },
      { tag: "open source", count: 2 },
    ]);
    assert.deepEqual(
      tagsFromItems(items).map((row) => row.tag),
      ["cli", "open source", "ux"],
    );
  });
});
