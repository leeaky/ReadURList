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

  return (
    <article className="item">
      <a className="item-title" href={item.url} target="_blank" rel="noopener noreferrer">
        {item.title || item.url}
      </a>
      {item.note ? <p className="item-note">{item.note}</p> : null}
      <p className="item-reason">
        {hasBody ? "Saved for today’s fill-in" : "Needs article text"}
      </p>
      {confirming ? (
        <div className="item-actions">
          <p className="item-reason confirm-prompt">Delete this stub?</p>
          <form action={deleteFormAction}>
            <button type="submit" disabled={deletePending}>
              {deletePending ? "Deleting…" : "Delete"}
            </button>
          </form>
          <button
            type="button"
            className="ghost"
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
      ) : (
        <div className="item-actions">
          <button type="button" className="ghost" onClick={() => setOpen((value) => !value)}>
            Paste article
          </button>
          <button
            type="button"
            className="ghost"
            onClick={() => {
              setOpen(false);
              setConfirming(true);
            }}
          >
            Delete
          </button>
        </div>
      )}
      {open && !confirming ? (
        <form action={formAction} className="paste-form">
          <textarea name="body" rows={8} placeholder="Paste article text…" />
          <input type="file" name="pdf" accept="application/pdf" />
          <button type="submit" disabled={pending}>
            {pending ? "Saving…" : "Save for fill-in"}
          </button>
          {!state.ok ? (
            <p className="error" role="alert" aria-live="polite">
              {state.error}
            </p>
          ) : null}
        </form>
      ) : null}
    </article>
  );
}
