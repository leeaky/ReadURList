"use client";

import { useActionState, useEffect, useMemo, useState } from "react";
import {
  bulkOrganize,
  remapVocabulary,
  type OrganizeState,
} from "@/app/actions";
import { useFilters } from "./AppFrame";
import {
  filterItems,
  subjectsFromItems,
  tagsFromItems,
  uniqueTopics,
} from "@/lib/filters";
import type { ItemRow } from "@/lib/supabase";

const initialState: OrganizeState = { ok: true, saved: false, updated: 0 };

export function OrganizeView({ items }: { items: ItemRow[] }) {
  const { search } = useFilters();
  const [subjectFilter, setSubjectFilter] = useState<string | null>(null);
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const [vocabOpen, setVocabOpen] = useState(false);
  const [mergeTo, setMergeTo] = useState("");
  const [bulkSubject, setBulkSubject] = useState("");
  const [bulkTags, setBulkTags] = useState("");

  const [remapState, remapAction, remapPending] = useActionState(
    remapVocabulary,
    initialState,
  );
  const [bulkState, bulkAction, bulkPending] = useActionState(
    bulkOrganize,
    initialState,
  );

  const subjects = subjectsFromItems(items);
  const tags = tagsFromItems(items);

  const visible = useMemo(
    () =>
      filterItems(items, {
        search,
        selectedSubjects: subjectFilter ? [subjectFilter] : [],
        selectedTags: tagFilter ? [tagFilter] : [],
        status: null,
      }),
    [items, search, subjectFilter, tagFilter],
  );

  const visibleIds = visible.map((item) => item.id);
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selected.has(id));

  useEffect(() => {
    if (remapState.ok && remapState.saved) {
      setSelected(new Set());
      setMergeTo("");
      setSubjectFilter(null);
      setTagFilter(null);
    }
  }, [remapState]);

  useEffect(() => {
    if (bulkState.ok && bulkState.saved) {
      setSelected(new Set());
      setBulkSubject("");
      setBulkTags("");
    }
  }, [bulkState]);

  function clickSubject(name: string) {
    setSubjectFilter((prev) => (prev === name ? null : name));
    setTagFilter(null);
    setMergeTo("");
  }

  function clickTag(tag: string) {
    setTagFilter((prev) => (prev === tag ? null : tag));
    setSubjectFilter(null);
    setMergeTo("");
  }

  function toggleId(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function toggleVisible() {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) {
        for (const id of visibleIds) {
          next.delete(id);
        }
      } else {
        for (const id of visibleIds) {
          next.add(id);
        }
      }
      return next;
    });
  }

  const mergeKind = subjectFilter ? "subject" : tagFilter ? "topic" : null;
  const mergeFrom = subjectFilter || tagFilter;
  const mergeCount = subjectFilter
    ? subjects.find((row) => row.name === subjectFilter)?.count ?? 0
    : tagFilter
      ? tags.find((row) => row.tag === tagFilter)?.count ?? 0
      : 0;
  const mergeTargets = subjectFilter
    ? subjects.map((row) => row.name).filter((name) => name !== subjectFilter)
    : tags.map((row) => row.tag).filter((tag) => tag !== tagFilter);

  const selectedIds = [...selected];
  const pending = remapPending || bulkPending;
  const actionError = !remapState.ok
    ? remapState.error
    : !bulkState.ok
      ? bulkState.error
      : null;
  const savedNote =
    (remapState.ok && remapState.saved
      ? `Updated ${remapState.updated} article${remapState.updated === 1 ? "" : "s"}.`
      : null) ||
    (bulkState.ok && bulkState.saved
      ? `Updated ${bulkState.updated} article${bulkState.updated === 1 ? "" : "s"}.`
      : null);

  return (
    <div className="organize-layout">
      <aside className="organize-vocab">
        <button
          type="button"
          className="sidebar-toggle"
          aria-expanded={vocabOpen}
          aria-controls="organize-vocab-panel"
          onClick={() => setVocabOpen((open) => !open)}
        >
          <span>Topics and tags</span>
          <svg
            className={vocabOpen ? "article-chevron is-open" : "article-chevron"}
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div
          id="organize-vocab-panel"
          className={vocabOpen ? "sidebar-panel is-open" : "sidebar-panel"}
        >
          {mergeKind && mergeFrom ? (
            <form action={remapAction} className="organize-merge">
              <input type="hidden" name="kind" value={mergeKind} />
              <input type="hidden" name="from" value={mergeFrom} />
              <p className="organize-merge-copy">
                Merge {mergeKind === "subject" ? "Topic" : "Tag"}{" "}
                <strong>{mergeFrom}</strong> ({mergeCount}) into
              </p>
              <input
                className="input"
                name="to"
                list="organize-merge-targets"
                value={mergeTo}
                onChange={(event) => setMergeTo(event.target.value)}
                placeholder="existing or new name"
                disabled={pending}
                required
              />
              <datalist id="organize-merge-targets">
                {mergeTargets.map((name) => (
                  <option key={name} value={name} />
                ))}
              </datalist>
              <button type="submit" className="btn btn-primary" disabled={pending}>
                {remapPending ? "Merging…" : "Apply merge"}
              </button>
            </form>
          ) : (
            <p className="page-blurb text-muted">
              Click a Topic or Tag to rename or merge it across the corpus.
            </p>
          )}
          <div className="sidebar-label">Topics</div>
          <div className="topic-list">
            {subjects.map((row) => (
              <button
                key={row.name}
                type="button"
                className="topic-row"
                aria-pressed={subjectFilter === row.name}
                onClick={() => clickSubject(row.name)}
              >
                <span>{row.name}</span>
                <span className="topic-count">{row.count}</span>
              </button>
            ))}
          </div>
          <div className="sidebar-label">Tags</div>
          <div className="tag-cloud">
            {tags.map((row) => (
              <button
                key={row.tag}
                type="button"
                className={
                  tagFilter === row.tag
                    ? "tag tag-accent tag-button"
                    : "tag tag-outline tag-button"
                }
                aria-pressed={tagFilter === row.tag}
                onClick={() => clickTag(row.tag)}
              >
                {row.tag}
                <span className="topic-count">{row.count}</span>
              </button>
            ))}
          </div>
        </div>
      </aside>

      <div className="organize-main">
        <div className="page-heading">
          <h1 className="page-title">Organize</h1>
          <span className="article-count text-muted">
            {visible.length} articles
            {selectedIds.length > 0 ? ` · ${selectedIds.length} selected` : ""}
          </span>
        </div>
        <p className="page-blurb text-muted">
          Rename or merge labels on the left. Select articles to set a Topic or
          add and remove Tags. Today’s ranking waits for the next daily job.
        </p>

        {visible.length === 0 ? (
          <p className="empty">No articles match your filters.</p>
        ) : (
          <>
            <label className="organize-select-all">
              <input
                type="checkbox"
                checked={allVisibleSelected}
                onChange={toggleVisible}
              />
              Select visible
            </label>
            <div className="article-list">
              {visible.map((item) => {
                const checked = selected.has(item.id);
                const topics = uniqueTopics(item.topics);
                return (
                  <label
                    key={item.id}
                    className={
                      checked
                        ? "organize-row is-selected"
                        : "organize-row"
                    }
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleId(item.id)}
                    />
                    <span className="organize-row-body">
                      <span className="article-meta-row">
                        {item.subject.trim() ? (
                          <span className="tag tag-outline">{item.subject}</span>
                        ) : null}
                      </span>
                      <span className="article-title">
                        {item.title || item.url}
                      </span>
                      {topics.length > 0 ? (
                        <span className="article-tags">
                          {topics.map((tag) => (
                            <span className="tag tag-accent" key={tag}>
                              {tag}
                            </span>
                          ))}
                        </span>
                      ) : null}
                    </span>
                  </label>
                );
              })}
            </div>
          </>
        )}

        {selectedIds.length > 0 ? (
          <div className="organize-bulk">
            <input type="hidden" name="ids" form="organize-bulk-subject" value={selectedIds.join(",")} />
            <input type="hidden" name="ids" form="organize-bulk-add" value={selectedIds.join(",")} />
            <input type="hidden" name="ids" form="organize-bulk-remove" value={selectedIds.join(",")} />
            <form id="organize-bulk-subject" action={bulkAction} className="organize-bulk-group">
              <input type="hidden" name="op" value="set-subject" />
              <label className="field">
                Topic
                <input
                  className="input"
                  name="subject"
                  list="organize-subjects"
                  value={bulkSubject}
                  onChange={(event) => setBulkSubject(event.target.value)}
                  placeholder="set Topic"
                  disabled={pending}
                  required
                />
              </label>
              <datalist id="organize-subjects">
                {subjects.map((row) => (
                  <option key={row.name} value={row.name} />
                ))}
              </datalist>
              <button type="submit" className="btn btn-primary" disabled={pending}>
                {bulkPending ? "Saving…" : "Set Topic"}
              </button>
            </form>
            <form id="organize-bulk-add" action={bulkAction} className="organize-bulk-group">
              <input type="hidden" name="op" value="add-topics" />
              <label className="field">
                Tags
                <input
                  className="input"
                  name="topics"
                  list="organize-tags"
                  value={bulkTags}
                  onChange={(event) => setBulkTags(event.target.value)}
                  placeholder="add or remove tags"
                  disabled={pending}
                />
              </label>
              <datalist id="organize-tags">
                {tags.map((row) => (
                  <option key={row.tag} value={row.tag} />
                ))}
              </datalist>
              <button type="submit" className="btn btn-secondary" disabled={pending}>
                Add Tags
              </button>
            </form>
            <form id="organize-bulk-remove" action={bulkAction} className="organize-bulk-group">
              <input type="hidden" name="op" value="remove-topics" />
              <input type="hidden" name="topics" value={bulkTags} />
              <button type="submit" className="btn btn-secondary" disabled={pending}>
                Remove Tags
              </button>
            </form>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setSelected(new Set())}
              disabled={pending}
            >
              Clear selection
            </button>
          </div>
        ) : null}

        {actionError ? (
          <p className="error" role="alert" aria-live="polite">
            {actionError}
          </p>
        ) : savedNote ? (
          <p className="article-note text-muted" aria-live="polite">
            {savedNote}
          </p>
        ) : null}
      </div>
    </div>
  );
}
