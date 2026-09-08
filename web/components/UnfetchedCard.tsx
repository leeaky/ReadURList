"use client";

import { useActionState, useEffect, useRef, useState } from "react";
import {
  deleteUnfetchedItem,
  submitArticleBody,
  type DeleteUnfetchedState,
  type SubmitArticleBodyState,
} from "@/app/actions";
import { hasExtractedBody, unfetchedIdleActionsDisabled } from "@/lib/unfetched";
import type { ItemRow } from "@/lib/supabase";

function formatDate(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toISOString().slice(0, 10);
}

export function UnfetchedCard({ item }: { item: ItemRow }) {
  const [mode, setMode] = useState<"idle" | "paste" | "pdf">("idle");
  const [confirming, setConfirming] = useState(false);
  const [pdfName, setPdfName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
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
      setMode("idle");
      setPdfName("");
      if (fileRef.current) {
        fileRef.current.value = "";
      }
    }
  }, [state]);

  const status = hasBody ? "Saved for today’s fill-in" : "Needs article text";
  const open = confirming || mode !== "idle";
  const idleActionsDisabled = unfetchedIdleActionsDisabled(mode);
  const cardClass = hasBody
    ? open
      ? "article-card is-queued is-open"
      : "article-card is-queued"
    : "article-card is-needs";

  function clearPdf() {
    setPdfName("");
    if (fileRef.current) {
      fileRef.current.value = "";
    }
  }

  function startPaste() {
    setConfirming(false);
    clearPdf();
    setMode("paste");
  }

  function startPdf() {
    setConfirming(false);
    setMode("pdf");
    fileRef.current?.click();
  }

  function startDelete() {
    setMode("idle");
    clearPdf();
    setConfirming(true);
  }

  return (
    <article className={cardClass}>
      <div className="article-header-main">
        <div className="article-meta-row">
          <span className={hasBody ? "tag tag-neutral" : "tag tag-outline"}>{status}</span>
        </div>
        {item.title.trim() ? (
          <>
            <div className="article-title">{item.title}</div>
            <a
              className="article-url"
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {item.url}
            </a>
          </>
        ) : (
          <a
            className="article-title"
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {item.url}
          </a>
        )}
        {item.note ? <p className="article-note text-muted">{item.note}</p> : null}
        <div className="article-date text-muted">Added {formatDate(item.created_at)}</div>
      </div>

      {confirming ? (
        <div className="article-body">
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
      ) : (
        <>
          <div className="article-actions">
            <button
              type="button"
              className={hasBody || idleActionsDisabled ? "btn btn-secondary" : "btn btn-primary"}
              aria-pressed={idleActionsDisabled ? undefined : mode === "paste"}
              onClick={startPaste}
              disabled={idleActionsDisabled}
            >
              Paste text
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              aria-pressed={idleActionsDisabled ? undefined : mode === "pdf"}
              onClick={startPdf}
              disabled={idleActionsDisabled}
            >
              Attach PDF
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={startDelete}
              disabled={idleActionsDisabled}
            >
              Delete
            </button>
          </div>
          {mode === "paste" ? (
            <form action={formAction} className="paste-form article-body">
              <div className="field">
                <label htmlFor={`body-${item.id}`}>Article text</label>
                <textarea
                  id={`body-${item.id}`}
                  className="input"
                  name="body"
                  rows={8}
                  placeholder="Paste the article text here"
                  autoFocus
                />
              </div>
              <div className="article-actions">
                <button type="submit" className="btn btn-primary" disabled={pending}>
                  {pending ? "Saving…" : "Save for fill-in"}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setMode("idle")}
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
            </form>
          ) : null}
          <form
            action={formAction}
            className="paste-form article-body"
            hidden={mode !== "pdf"}
          >
            <input
              ref={fileRef}
              id={`pdf-${item.id}`}
              className="visually-hidden"
              type="file"
              name="pdf"
              accept="application/pdf"
              aria-label="PDF file"
              tabIndex={-1}
              onChange={(event) => {
                setPdfName(event.target.files?.[0]?.name ?? "");
                setMode("pdf");
              }}
            />
            {mode === "pdf" ? (
              <>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => fileRef.current?.click()}
                >
                  {pdfName || "Choose PDF"}
                </button>
                <p className="article-date text-muted">PDF, max 3.5 MB. Text is extracted on save.</p>
                <div className="article-actions">
                  <button type="submit" className="btn btn-primary" disabled={pending || !pdfName}>
                    {pending ? "Saving…" : "Save for fill-in"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setMode("idle");
                      clearPdf();
                    }}
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
              </>
            ) : null}
          </form>
        </>
      )}
    </article>
  );
}
