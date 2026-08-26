"use client";

import { useState } from "react";
import { submitArticleBody } from "@/app/actions";
import type { ItemRow } from "@/lib/supabase";

export function UnfetchedCard({ item }: { item: ItemRow }) {
  const [open, setOpen] = useState(false);
  const hasBody = Boolean((item.extracted_text || "").trim());
  const action = submitArticleBody.bind(null, item.id);

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
        <form action={action} className="paste-form">
          <textarea name="body" rows={8} placeholder="Paste article text…" />
          <input type="file" name="pdf" accept="application/pdf" />
          <button type="submit">Save for fill-in</button>
        </form>
      ) : null}
    </article>
  );
}
