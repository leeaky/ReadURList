# Unfetched queue UI (issue #14)

**Date:** 2026-08-27  
**Issue:** Airtable #14 (ReadURList)  
**Status:** Approved for implementation planning

## Problem

`/unfetched` is a single undifferentiated list of `pending_body` stubs. After a successful paste/PDF save, the form stays open with no acknowledgment. There is no way to drop a stub whose URL is gone. Items that already have a body sit next to items that still need one, so it is unclear what still needs work.

## Goal

Rethink Unfetched as a two-section work queue:

1. **Needs article text** — stubs with no body yet.
2. **Saved for today’s fill-in** — stubs that already have `extracted_text`, waiting for the daily NUC Groq pass.

After a successful save, close the paste form and show an acknowledgment. Allow paste-again (overwrite) and delete on both sections. Delete permanently removes the stub, with an on-card confirm step. Both sections persist across reload until Groq marks the item `ready` or the user deletes it.

## Non-goals

- Calling Groq from Vercel, or completing ingest on save.
- Session-only “just saved” tray that vanishes on reload.
- Changing Telegram ingest, digest scheduling, or ranking.
- Issue #12 (save URL on fetch error) beyond what already shipped.
- Visual redesign of the rest of the site (tabs, cards, brand).
- Prefilling the textarea with the previously saved body.
- Soft-delete / abandoned status / undo window.

## Page structure

Keep `/unfetched` as one page. Split the existing `pending_body` query into two lists:

| Section | Rule | Empty |
|---------|------|--------|
| Needs article text | `ingest_status = pending_body` and trimmed `extracted_text` is empty | Hide the heading and list |
| Saved for today’s fill-in | `ingest_status = pending_body` and trimmed `extracted_text` is non-empty | Hide the heading and list |

If both lists are empty, keep the current page empty copy: “No items waiting for article text.”

Order in each section: newest first (`created_at` desc), same as today.

Copy:

- Page title: **Unfetched**
- Section 1: **Needs article text**
- Section 2: **Saved for today’s fill-in**
- Needs-text status line: **Needs article text**
- Queued status / ack line: **Saved for today’s fill-in**
- Paste toggle: **Paste article** (same button opens and closes the form)
- Save: **Save for fill-in** (pending: **Saving…**)
- Delete: **Delete**
- Confirm: **Delete this stub?** with **Delete** and **Cancel**

## Card behavior

Every Unfetched card shows title (link to URL), optional fetch `note`, status line, then actions: **Paste article** and **Delete**.

### Save

1. User opens **Paste article** (textarea + PDF, same as today).
2. On save error: form stays open; existing error line stays.
3. On save success: form closes and clears; card now belongs in **Saved for today’s fill-in** (revalidate `/unfetched`); status line is the acknowledgment **Saved for today’s fill-in**.
4. Paste-again on a queued card is a replacement save: empty form, overwrite `extracted_text`, stay in the saved section, form closes, same ack.

Do not put the stored body back into the textarea.

### Delete

1. **Delete** reveals an on-card confirm (**Delete this stub?** / **Delete** / **Cancel**). No `window.confirm`.
2. **Cancel** returns to the normal actions.
3. Confirmed delete: hard-delete that `items` row if and only if `ingest_status = pending_body`.
4. On success: card disappears (revalidate `/unfetched`).
5. On failure: card remains; show an error on the card; leave confirm UI so they can retry or cancel.

`cluster_items` cascade on item delete. `daily_picks` does not. Stubs are excluded from ranking, so picks should not exist; if a FK still blocks, surface the error instead of a partial delete. Do not add a migration for this.

## Data flow

No schema change. Continue to use `ingest_status` and `extracted_text`.

| Event | Writes | Unfetched result |
|-------|--------|------------------|
| Save paste/PDF | `extracted_text` (trim); `ingest_status` stays `pending_body` | Card moves to saved section |
| Delete | `DELETE` row where `id` matches and `ingest_status = pending_body` | Card gone |
| Daily NUC completion (existing) | Groq fields; `ingest_status = ready` | Item leaves Unfetched |

Server actions:

- Keep `submitArticleBody` for save (close form in the client on `ok: true`).
- Add `deleteUnfetchedItem(itemId)` that refuses anything not `pending_body`.

## Error handling

- Invalid id / not `pending_body`: return `{ ok: false, error }` — do not throw a 500.
- Save validation unchanged (empty body, PDF type/size, extract failure).
- Delete FK / database error: return a short error string; do not leak internals.

## Testing

- Client: after successful save, paste form is not visible and the card’s status is the ack (manual / browser check on `/unfetched`).
- Delete confirm must be cancelled without calling the server; confirm must remove a `pending_body` stub.
- Do not delete `ready` items even if a crafted id is posted.
- Existing complete-pending tests stay the source of truth for “queued body becomes ready overnight.”

## Implementation sketch

- `web/app/unfetched/page.tsx` — split items into two arrays; two section titles.
- `web/components/UnfetchedCard.tsx` — close form on success; delete confirm; queued vs needs-text copy.
- `web/app/actions.ts` — `deleteUnfetchedItem`; possibly return enough to let the client close the form from `useActionState`.
- `web/app/globals.css` — only if confirm/actions need a small layout tweak; match existing `.item-actions` / `.error`.
