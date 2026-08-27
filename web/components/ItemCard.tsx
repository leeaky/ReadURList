"use client";

import { useActionState, useEffect, useState } from "react";
import {
  sendItemToUnfetched,
  setReadState,
  updateItemMetadata,
  type SendToUnfetchedState,
  type UpdateItemMetadataState,
} from "@/app/actions";
import type { ItemRow } from "@/lib/supabase";

function formatWhen(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 16).replace("T", " ");
}

export function ItemCard({
  item,
  reason,
}: {
  item: ItemRow;
  reason?: string;
}) {
  const read = Boolean(item.read_at);
  const toggle = setReadState.bind(null, item.id, !read);
  const topics = item.topics ?? [];
  const [editing, setEditing] = useState(false);
  const [confirmingSend, setConfirmingSend] = useState(false);
  const action = updateItemMetadata.bind(null, item.id);
  const initialState: UpdateItemMetadataState = { ok: true, saved: false };
  const [state, formAction, pending] = useActionState(action, initialState);
  const sendAction = sendItemToUnfetched.bind(null, item.id);
  const sendInitial: SendToUnfetchedState = { ok: true, sent: false };
  const [sendState, sendFormAction, sendPending] = useActionState(
    sendAction,
    sendInitial,
  );

  useEffect(() => {
    if (state.ok && state.saved) {
      setEditing(false);
      setConfirmingSend(false);
    }
  }, [state]);

  return (
    <article className="item">
      {editing ? (
        <>
          <form action={formAction} className="paste-form">
            <label>
              Headline
              <input
                type="text"
                name="title"
                defaultValue={item.title}
                maxLength={1024}
                required
              />
            </label>
            <label>
              Description
              <textarea
                name="snapshot"
                rows={4}
                defaultValue={item.snapshot}
              />
            </label>
            <label>
              Subject
              <input
                type="text"
                name="subject"
                defaultValue={item.subject}
                maxLength={256}
              />
            </label>
            <label>
              Topics
              <input
                type="text"
                name="topics"
                defaultValue={topics.join(", ")}
                placeholder="Comma-separated"
              />
            </label>
            {confirmingSend ? null : (
              <div className="item-actions">
                <button type="submit" disabled={pending}>
                  {pending ? "Saving…" : "Save"}
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => setEditing(false)}
                  disabled={pending}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => setConfirmingSend(true)}
                  disabled={pending}
                >
                  Send to Unfetched
                </button>
                {!state.ok ? (
                  <p className="error" role="alert" aria-live="polite">
                    {state.error}
                  </p>
                ) : null}
              </div>
            )}
          </form>
          {confirmingSend ? (
            <div className="item-actions">
              <p className="item-reason confirm-prompt">
                Send to Unfetched? This clears the stored article text.
              </p>
              <form action={sendFormAction}>
                <button type="submit" disabled={sendPending}>
                  {sendPending ? "Sending…" : "Send to Unfetched"}
                </button>
              </form>
              <button
                type="button"
                className="ghost"
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
        </>
      ) : (
        <>
          <a
            className="item-title"
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {item.title || item.url}
          </a>
          {item.snapshot ? <p className="item-summary">{item.snapshot}</p> : null}
          {reason ? <p className="item-reason">Why: {reason}</p> : null}
          {item.similar_to_item_id ? (
            <p className="item-note">
              Possible duplicate of item #{item.similar_to_item_id}
            </p>
          ) : null}
          <div className="chips">
            {item.subject ? <span className="chip">{item.subject}</span> : null}
            {topics.slice(0, 8).map((t) => (
              <span className="chip" key={t}>
                {t}
              </span>
            ))}
          </div>
        </>
      )}
      <div className="item-meta">
        <a href={item.url} target="_blank" rel="noopener noreferrer">
          {item.url}
        </a>
        <time dateTime={item.created_at}>{formatWhen(item.created_at)}</time>
        {read ? <span>Read {formatWhen(item.read_at)}</span> : <span>Unread</span>}
        <form action={toggle}>
          <button type="submit" className={read ? "ghost" : undefined}>
            {read ? "Mark unread" : "Mark read"}
          </button>
        </form>
        {editing ? null : (
          <button type="button" className="ghost" onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
      </div>
    </article>
  );
}
