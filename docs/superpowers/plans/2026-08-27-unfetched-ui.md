# Unfetched Queue UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `/unfetched` into Needs article text vs Saved for today’s fill-in, close the paste form after a successful save, and let the user hard-delete a stub after an on-card confirm.

**Architecture:** Keep `ingest_status` / `extracted_text` as the split. A small pure helper partitions the existing `pending_body` query. `submitArticleBody` returns a `saved` flag so the client can close the form. A new `deleteUnfetchedItem` server action deletes only `pending_body` rows. No schema change and no Groq on Vercel.

**Tech Stack:** Next.js 15 App Router, React 19 `useActionState`, Supabase JS (service role), Node built-in test runner (`node --experimental-strip-types --test`).

## Global Constraints

- Copy is verbatim from the spec: section titles **Needs article text** and **Saved for today’s fill-in**; status/ack **Needs article text** / **Saved for today’s fill-in**; buttons **Paste article**, **Save for fill-in**, **Saving…**, **Delete**; confirm **Delete this stub?** with **Delete** and **Cancel**.
- Empty page copy stays **No items waiting for article text.**
- Hide a section heading when that list is empty.
- Both sections persist across reload until Groq sets `ingest_status = ready` or the user deletes.
- Hard-delete only `pending_body` rows. Do not use `window.confirm`. Do not prefill the textarea. Do not add a migration.
- Invalid id / not `pending_body` / FK failure return `{ ok: false, error }` — do not throw a 500 for those cases.
- Do not call Groq from Vercel. Do not complete ingest on save.

## File structure

- Create: `web/lib/unfetched.ts` — `hasExtractedBody`, `partitionUnfetched`, `unfetchedDeleteGuard`
- Create: `web/lib/unfetched.test.ts` — Node tests for those helpers
- Modify: `web/app/unfetched/page.tsx` — two sections
- Modify: `web/components/UnfetchedCard.tsx` — close form on save; delete confirm
- Modify: `web/app/actions.ts` — `saved` on submit success; `deleteUnfetchedItem`
- Modify: `web/app/globals.css` — confirm row if flex wrap needs a full-width prompt
- Modify: `CHANGELOG.md` — Unfetched queue behavior

---

### Task 1: Partition and delete-guard helpers

**Files:**
- Create: `web/lib/unfetched.ts`
- Create: `web/lib/unfetched.test.ts`

**Interfaces:**
- Consumes: `ItemRow.extracted_text` shape (`string | null | undefined`)
- Produces:
  - `hasExtractedBody(text: string | null | undefined): boolean`
  - `partitionUnfetched<T extends { extracted_text?: string | null }>(items: T[]): { needsText: T[]; saved: T[] }`
  - `unfetchedDeleteGuard(row: { ingest_status: string } | null): string | null` — `null` means allowed; otherwise the error string `"Item is not awaiting a body."`

- [ ] **Step 1: Write the failing tests**

```typescript
// web/lib/unfetched.test.ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  hasExtractedBody,
  partitionUnfetched,
  unfetchedDeleteGuard,
} from "./unfetched.ts";

describe("hasExtractedBody", () => {
  it("is false for empty, whitespace, null, and undefined", () => {
    assert.equal(hasExtractedBody(""), false);
    assert.equal(hasExtractedBody("   "), false);
    assert.equal(hasExtractedBody(null), false);
    assert.equal(hasExtractedBody(undefined), false);
  });

  it("is true when trimmed text is non-empty", () => {
    assert.equal(hasExtractedBody("hello"), true);
    assert.equal(hasExtractedBody("  hello  "), true);
  });
});

describe("partitionUnfetched", () => {
  it("splits needs-text vs saved and preserves order", () => {
    const items = [
      { id: 1, extracted_text: "" },
      { id: 2, extracted_text: "body" },
      { id: 3, extracted_text: "  " },
      { id: 4, extracted_text: "more" },
    ];
    const { needsText, saved } = partitionUnfetched(items);
    assert.deepEqual(
      needsText.map((i) => i.id),
      [1, 3],
    );
    assert.deepEqual(
      saved.map((i) => i.id),
      [2, 4],
    );
  });
});

describe("unfetchedDeleteGuard", () => {
  it("allows pending_body", () => {
    assert.equal(unfetchedDeleteGuard({ ingest_status: "pending_body" }), null);
  });

  it("refuses missing rows and ready items", () => {
    assert.equal(unfetchedDeleteGuard(null), "Item is not awaiting a body.");
    assert.equal(
      unfetchedDeleteGuard({ ingest_status: "ready" }),
      "Item is not awaiting a body.",
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web && node --experimental-strip-types --test lib/unfetched.test.ts`

Expected: FAIL (cannot find module `./unfetched.ts`)

- [ ] **Step 3: Write minimal implementation**

```typescript
// web/lib/unfetched.ts
export function hasExtractedBody(text: string | null | undefined): boolean {
  return Boolean((text || "").trim());
}

export function partitionUnfetched<T extends { extracted_text?: string | null }>(
  items: T[],
): { needsText: T[]; saved: T[] } {
  const needsText: T[] = [];
  const saved: T[] = [];
  for (const item of items) {
    if (hasExtractedBody(item.extracted_text)) {
      saved.push(item);
    } else {
      needsText.push(item);
    }
  }
  return { needsText, saved };
}

export function unfetchedDeleteGuard(
  row: { ingest_status: string } | null,
): string | null {
  if (!row || row.ingest_status !== "pending_body") {
    return "Item is not awaiting a body.";
  }
  return null;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && node --experimental-strip-types --test lib/unfetched.test.ts`

Expected: PASS (3 suites, all tests pass)

- [ ] **Step 5: Commit**

```bash
git add web/lib/unfetched.ts web/lib/unfetched.test.ts
git commit -m "Add Unfetched partition and delete-guard helpers."
```

---

### Task 2: Two sections on `/unfetched`

**Files:**
- Modify: `web/app/unfetched/page.tsx`

**Interfaces:**
- Consumes: `partitionUnfetched` from `web/lib/unfetched.ts`
- Produces: page renders **Needs article text** then **Saved for today’s fill-in**; hides empty sections; both-empty uses existing empty copy

- [ ] **Step 1: Split the page**

Replace the single map with:

```tsx
import { UnfetchedCard } from "@/components/UnfetchedCard";
import { Shell } from "@/components/ui";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";
import { partitionUnfetched } from "@/lib/unfetched";

export const dynamic = "force-dynamic";

export default async function UnfetchedPage() {
  const db = supabaseAdmin();
  const { data, error } = await db
    .from("items")
    .select(
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id, ingest_status, extracted_text, note",
    )
    .eq("ingest_status", "pending_body")
    .order("created_at", { ascending: false });
  if (error) {
    throw new Error(error.message);
  }
  const items = (data || []) as ItemRow[];
  const { needsText, saved } = partitionUnfetched(items);

  return (
    <Shell current="/unfetched">
      <h2 className="section-title">Unfetched</h2>
      {items.length === 0 ? (
        <p className="empty">No items waiting for article text.</p>
      ) : (
        <>
          {needsText.length > 0 ? (
            <section>
              <h3 className="section-title">Needs article text</h3>
              {needsText.map((item) => (
                <UnfetchedCard key={item.id} item={item} />
              ))}
            </section>
          ) : null}
          {saved.length > 0 ? (
            <section>
              <h3 className="section-title">Saved for today’s fill-in</h3>
              {saved.map((item) => (
                <UnfetchedCard key={item.id} item={item} />
              ))}
            </section>
          ) : null}
        </>
      )}
    </Shell>
  );
}
```

- [ ] **Step 2: Verify TypeScript for the page**

`web/lib/unfetched.test.ts` is excluded from `tsc` (`**/*.test.ts`) because Node tests import `./unfetched.ts`.

Run: `cd web && npx tsc --noEmit --pretty false`

Expected: no errors from `app/unfetched/page.tsx`. A pre-existing `unpdf` types error in `lib/pdf.ts` is out of scope.

- [ ] **Step 3: Commit**

```bash
git add web/app/unfetched/page.tsx
git commit -m "Split Unfetched into needs-text and saved sections."
```

---

### Task 3: Close paste form on successful save

**Files:**
- Modify: `web/app/actions.ts` — `SubmitArticleBodyState`
- Modify: `web/components/UnfetchedCard.tsx`

**Interfaces:**
- Consumes: existing `submitArticleBody` validation
- Produces: `SubmitArticleBodyState = { ok: true; saved: boolean } | { ok: false; error: string }`. Initial client state `{ ok: true, saved: false }`. Success return `{ ok: true, saved: true }`. Card closes the form when `state.ok && state.saved`. Status copy: **Needs article text** vs **Saved for today’s fill-in**.

- [ ] **Step 1: Return a saved flag from the action**

Change the type and returns in `web/app/actions.ts`:

```typescript
export type SubmitArticleBodyState =
  | { ok: true; saved: boolean }
  | { ok: false; error: string };
```

Keep every `{ ok: false, error: "..." }` return as-is.

Change the success return from `return { ok: true };` to `return { ok: true, saved: true };`.

- [ ] **Step 2: Close the form in the card**

In `UnfetchedCard.tsx`:

```tsx
"use client";

import { useActionState, useEffect, useState } from "react";
import {
  submitArticleBody,
  type SubmitArticleBodyState,
} from "@/app/actions";
import { hasExtractedBody } from "@/lib/unfetched";
import type { ItemRow } from "@/lib/supabase";

export function UnfetchedCard({ item }: { item: ItemRow }) {
  const [open, setOpen] = useState(false);
  const hasBody = hasExtractedBody(item.extracted_text);
  const action = submitArticleBody.bind(null, item.id);
  const initialState: SubmitArticleBodyState = { ok: true, saved: false };
  const [state, formAction, pending] = useActionState(action, initialState);

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
      <div className="item-actions">
        <button type="button" className="ghost" onClick={() => setOpen((value) => !value)}>
          Paste article
        </button>
      </div>
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
```

Unmounting the form on close clears textarea and file input. Do not set `defaultValue` from `extracted_text`.

- [ ] **Step 3: Commit**

```bash
git add web/app/actions.ts web/components/UnfetchedCard.tsx
git commit -m "Close Unfetched paste form after a successful save."
```

---

### Task 4: Delete stub with on-card confirm

**Files:**
- Modify: `web/app/actions.ts`
- Modify: `web/components/UnfetchedCard.tsx`
- Modify: `web/app/globals.css`

**Interfaces:**
- Consumes: `unfetchedDeleteGuard` from `web/lib/unfetched.ts`
- Produces: `DeleteUnfetchedState = { ok: true } | { ok: false; error: string }`; `deleteUnfetchedItem(itemId, previousState, formData): Promise<DeleteUnfetchedState>`

- [ ] **Step 1: Add the delete server action**

Append to `web/app/actions.ts`:

```typescript
export type DeleteUnfetchedState =
  | { ok: true }
  | { ok: false; error: string };

export async function deleteUnfetchedItem(
  itemId: number,
  _previousState: DeleteUnfetchedState,
  _formData: FormData,
): Promise<DeleteUnfetchedState> {
  if (!Number.isInteger(itemId) || itemId <= 0) {
    return { ok: false, error: "Invalid article." };
  }

  const db = supabaseAdmin();
  const { data: row, error: readError } = await db
    .from("items")
    .select("id, ingest_status")
    .eq("id", itemId)
    .maybeSingle();
  if (readError) {
    return { ok: false, error: "Could not delete this stub." };
  }
  const blocked = unfetchedDeleteGuard(
    row ? { ingest_status: String(row.ingest_status) } : null,
  );
  if (blocked) {
    return { ok: false, error: blocked };
  }

  const { error } = await db
    .from("items")
    .delete()
    .eq("id", itemId)
    .eq("ingest_status", "pending_body");
  if (error) {
    return { ok: false, error: "Could not delete this stub." };
  }
  revalidatePath("/unfetched");
  return { ok: true };
}
```

Import `unfetchedDeleteGuard` from `@/lib/unfetched`.

- [ ] **Step 2: Wire confirm UI on the card**

Keep Task 3 paste behavior. Add `confirming` state. When `confirming` is true, hide Paste article / Delete and the paste form; show the confirm prompt. Cancel sets `confirming` to false. Opening confirm closes the paste form (`setOpen(false)`).

```tsx
const [confirming, setConfirming] = useState(false);
const deleteAction = deleteUnfetchedItem.bind(null, item.id);
const deleteInitial: DeleteUnfetchedState = { ok: true };
const [deleteState, deleteFormAction, deletePending] = useActionState(
  deleteAction,
  deleteInitial,
);

// actions block:
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
```

Only render the paste form when `open && !confirming`.

- [ ] **Step 3: CSS for the confirm prompt**

Add to `web/app/globals.css`:

```css
.confirm-prompt {
  flex: 1 1 100%;
  margin: 0;
}
```

This puts **Delete this stub?** on its own row above the buttons inside `.item-actions`.

- [ ] **Step 4: Run helper tests again**

Run: `cd web && node --experimental-strip-types --test lib/unfetched.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/app/actions.ts web/components/UnfetchedCard.tsx web/app/globals.css
git commit -m "Let Unfetched delete pending_body stubs after confirm."
```

---

### Task 5: Changelog and browser verification

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Tasks 1–4 behavior
- Produces: changelog line; live check of `/unfetched`

- [ ] **Step 1: Changelog**

Under `## [Unreleased]` → `### Changed`, add:

```markdown
- Unfetched splits needs-text vs saved-for-fill-in; paste form closes on save; stubs can be deleted after confirm.
```

- [ ] **Step 2: Browser-check `/unfetched`** (dev server on port 3000, password gate)

1. Needs-text card: status **Needs article text**; **Paste article** and **Delete** visible.
2. Open paste, submit empty → error, form stays open.
3. Paste text and save → form closes; card is under **Saved for today’s fill-in** with ack **Saved for today’s fill-in**.
4. On a saved card, open paste again (empty, not prefilled), save replacement → form closes, still in saved section.
5. **Delete** → **Delete this stub?** / **Delete** / **Cancel**. Cancel returns to actions without removing the card.
6. Confirm Delete → card gone.
7. Reload: queued items with bodies still in **Saved for today’s fill-in** (not a session tray).
8. If both sections empty: **No items waiting for article text.**

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "Note Unfetched queue UI in the changelog."
```
