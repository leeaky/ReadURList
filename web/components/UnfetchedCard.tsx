"use client";

import { useActionState, useState } from "react";
import {
  submitArticleBody,
  type SubmitArticleBodyState,
} from "@/app/actions";
import type { ItemRow } from "@/lib/supabase";

export function UnfetchedCard({ item }: { item: ItemRow }) {
  const [open, setOpen] = useState(false);
  const hasBody = Boolean((item.extracted_text || "").trim());
  const action = submitArticleBody.bind(null, item.id);
  const initialState: SubmitArticleBodyState = { ok: true };
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <article className="item">
      <a className="item-title" href={item.url} target="_blank" rel="noopener noreferrer">
        {item.title || item.url}
      </a>
      {item.note ? <p className="item-note">{item.note}</p> : null}
      <p className="item-reason">
        {hasBody ? "Queued for today’s fill-in" : "Needs article text"}
      </p>
      <button type="button" className="ghost" onClick={() => setOpen((value) => !value)}>
        Paste article
      </button>
      {open ? (
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
