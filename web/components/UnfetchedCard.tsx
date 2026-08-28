"use client";

import { useActionState, useEffect, useState } from "react";
import {
  deleteUnfetchedItem,
  submitArticleBody,
  type DeleteUnfetchedState,
  type SubmitArticleBodyState,
} from "@/app/actions";
import { hasExtractedBody } from "@/lib/unfetched";
import type { ItemRow } from "@/lib/supabase";

function formatDate(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toISOString().slice(0, 10);
}

export function UnfetchedCard({ item }: { item: ItemRow }) {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const hasBody = hasExtractedBody(item.extracted_text);
  const action = submitArticleBody.bind(null, item.id);
  const initialState: SubmitArticleBodyState = { ok: true, saved: false };
  const [state, formAction, pending] = useActionState(action, initialState);
  const deleteAction = deleteUnfetchedItem.bind(null, item.id);
  const deleteInitial: DeleteUnfetchedState = { ok: true };
  const [deleteState, deleteFormAction, deletePending] = useActionState(
    deleteAction,
    deleteInitial,
  );

  useEffect(() => {
    if (state.ok && state.saved) {
      setOpen(false);
    }
  }, [state]);

  const status = hasBody ? "Saved for today’s fill-in" : "Needs article text";

  return (
    <div>
      <div className="unfetched-row">
        <button
          type="button"
          className="article-header"
          onClick={() => {
            setConfirming(false);
            setOpen((value) => !value);
          }}
          aria-expanded={open}
        >
          <div className="article-header-main">
            <div className="unfetched-url">{item.url}</div>
            <div className="unfetched-date text-muted">
              Added {formatDate(item.created_at)} · {status}
            </div>
            {item.note ? <div className="unfetched-date text-muted">{item.note}</div> : null}
          </div>
        </button>
        {confirming ? null : (
          <form action={deleteFormAction}>
            <button
              type="submit"
              className="btn btn-secondary btn-icon"
              aria-label="Delete"
              onClick={(event) => {
                event.preventDefault();
                setOpen(false);
                setConfirming(true);
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 6h18" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                <path d="M10 11v6" />
                <path d="M14 11v6" />
              </svg>
            </button>
          </form>
        )}
      </div>
      {confirming ? (
        <div className="unfetched-expand">
          <div className="article-actions">
            <p className="article-why text-muted confirm-prompt">Delete this stub?</p>
            <form action={deleteFormAction}>
              <button type="submit" className="btn btn-primary" disabled={deletePending}>
                {deletePending ? "Deleting…" : "Delete"}
              </button>
            </form>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setConfirming(false)}
              disabled={deletePending}
            >
              Cancel
            </button>
            {!deleteState.ok ? (
              <p className="error" role="alert" aria-live="polite">
                {deleteState.error}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
      {open && !confirming ? (
        <div className="unfetched-expand">
          <form action={formAction} className="paste-form">
            <textarea className="input" name="body" rows={8} placeholder="Paste article text…" />
            <input type="file" name="pdf" accept="application/pdf" />
            <button type="submit" className="btn btn-primary" disabled={pending}>
              {pending ? "Saving…" : "Save for fill-in"}
            </button>
            {!state.ok ? (
              <p className="error" role="alert" aria-live="polite">
                {state.error}
              </p>
            ) : null}
          </form>
        </div>
      ) : null}
    </div>
  );
}
