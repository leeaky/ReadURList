"use client";

import { useActionState, useEffect, useState } from "react";
import {
  sendItemToUnfetched,
  setReadState,
  updateItemMetadata,
  type SendToUnfetchedState,
  type UpdateItemMetadataState,
} from "@/app/actions";
import { parseTopicList } from "@/lib/item-edit";
import type { ItemRow } from "@/lib/supabase";

function formatDate(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toISOString().slice(0, 10);
}

export function ItemCard({
  item,
  reason,
  rank,
  subjects,
}: {
  item: ItemRow;
  reason?: string;
  rank?: number;
  subjects: string[];
}) {
  const read = Boolean(item.read_at);
  const toggle = setReadState.bind(null, item.id, !read);
  const topics = item.topics ?? [];
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirmingSend, setConfirmingSend] = useState(false);
  const [draftSubject, setDraftSubject] = useState(item.subject);
  const [draftTopics, setDraftTopics] = useState(topics);
  const [tagInput, setTagInput] = useState("");
  const action = updateItemMetadata.bind(null, item.id);
  const initialState: UpdateItemMetadataState = { ok: true, saved: false };
  const [state, formAction, pending] = useActionState(action, initialState);
  const sendAction = sendItemToUnfetched.bind(null, item.id);
  const sendInitial: SendToUnfetchedState = { ok: true, sent: false };
  const [sendState, sendFormAction, sendPending] = useActionState(
    sendAction,
    sendInitial,
  );

  const subjectOptions = subjects.includes(item.subject)
    ? subjects
    : item.subject.trim()
      ? [item.subject, ...subjects]
      : subjects;

  useEffect(() => {
    if (state.ok && state.saved) {
      setEditing(false);
      setConfirmingSend(false);
    }
  }, [state]);

  function startEdit() {
    setDraftSubject(item.subject);
    setDraftTopics(item.topics ?? []);
    setTagInput("");
    setConfirmingSend(false);
    setEditing(true);
    setExpanded(true);
  }

  function commitTag() {
    const next = parseTopicList([...draftTopics, tagInput].join(", "));
    setDraftTopics(next);
    setTagInput("");
  }

  return (
    <article className={read ? "article-card is-read" : "article-card"}>
      <button
        type="button"
        className="article-header"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        {rank != null ? <div className="article-rank">{rank}</div> : null}
        <div className="article-header-main">
          <div className="article-meta-row">
            {item.subject.trim() ? (
              <span className="tag tag-outline">{item.subject}</span>
            ) : null}
            {read ? <span className="read-label text-muted">Read</span> : null}
          </div>
          <div className="article-title">
            {item.title || item.url}
          </div>
          {item.snapshot ? <p className="article-teaser text-muted">{item.snapshot}</p> : null}
        </div>
        <svg
          className={expanded ? "article-chevron is-open" : "article-chevron"}
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
      {expanded ? (
        <div className="article-body">
          {editing ? (
            <form action={formAction} className="paste-form">
              <div className="field">
                <label htmlFor={`title-${item.id}`}>Headline</label>
                <input
                  id={`title-${item.id}`}
                  className="input"
                  type="text"
                  name="title"
                  defaultValue={item.title}
                  maxLength={1024}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor={`snapshot-${item.id}`}>Description</label>
                <textarea
                  id={`snapshot-${item.id}`}
                  className="input"
                  name="snapshot"
                  rows={4}
                  defaultValue={item.snapshot}
                />
              </div>
              <div className="field" style={{ maxWidth: 260 }}>
                <label htmlFor={`subject-${item.id}`}>Topic</label>
                {subjectOptions.length > 0 ? (
                  <select
                    id={`subject-${item.id}`}
                    className="input"
                    name="subject"
                    value={draftSubject}
                    onChange={(event) => setDraftSubject(event.target.value)}
                  >
                    {subjectOptions.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={`subject-${item.id}`}
                    className="input"
                    type="text"
                    name="subject"
                    value={draftSubject}
                    onChange={(event) => setDraftSubject(event.target.value)}
                    maxLength={256}
                  />
                )}
              </div>
              <input type="hidden" name="topics" value={draftTopics.join(", ")} />
              <div className="edit-tags">
                {draftTopics.map((tag) => (
                  <span className="tag tag-neutral" key={tag}>
                    {tag}
                    <button
                      type="button"
                      className="tag-remove"
                      aria-label={`Remove ${tag}`}
                      onClick={() =>
                        setDraftTopics((prev) => prev.filter((itemTag) => itemTag !== tag))
                      }
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" aria-hidden="true">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </span>
                ))}
                <input
                  className="input edit-tag-input"
                  placeholder="add tag, Enter"
                  value={tagInput}
                  onChange={(event) => setTagInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      commitTag();
                    }
                  }}
                />
              </div>
              {confirmingSend ? null : (
                <div className="article-actions">
                  <button type="submit" className="btn btn-primary" disabled={pending}>
                    {pending ? "Saving…" : "Save"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setEditing(false)}
                    disabled={pending}
                  >
                    Cancel
                  </button>
                  {!state.ok ? (
                    <p className="error" role="alert" aria-live="polite">
                      {state.error}
                    </p>
                  ) : null}
                </div>
              )}
            </form>
          ) : (
            <>
              {item.snapshot ? <p className="article-summary">{item.snapshot}</p> : null}
              {reason ? <p className="article-why text-muted">Why: {reason}</p> : null}
              {item.similar_to_item_id ? (
                <p className="article-note text-muted">
                  Possible duplicate of item #{item.similar_to_item_id}
                </p>
              ) : null}
              {topics.length > 0 ? (
                <div className="article-tags">
                  {topics.map((tag) => (
                    <span className="tag tag-accent" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
              <a
                className="article-url"
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                {item.url}
              </a>
              <div className="article-date text-muted">{formatDate(item.created_at)}</div>
              {confirmingSend ? null : (
                <div className="article-actions">
                  <form action={toggle}>
                    <button type="submit" className="btn btn-primary">
                      {read ? "Mark unread" : "Mark read"}
                    </button>
                  </form>
                  <button type="button" className="btn btn-secondary" onClick={startEdit}>
                    Edit
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setConfirmingSend(true)}
                  >
                    Send to Unfetched
                  </button>
                </div>
              )}
            </>
          )}
          {confirmingSend ? (
            <div className="article-actions">
              <p className="article-why text-muted confirm-prompt">
                Send to Unfetched? This clears the stored article text.
              </p>
              <form action={sendFormAction}>
                <button type="submit" className="btn btn-primary" disabled={sendPending}>
                  {sendPending ? "Sending…" : "Send to Unfetched"}
                </button>
              </form>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setConfirmingSend(false)}
                disabled={sendPending}
              >
                Cancel
              </button>
              {!sendState.ok ? (
                <p className="error" role="alert" aria-live="polite">
                  {sendState.error}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
