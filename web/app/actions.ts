"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  itemEditGuard,
  parseItemEdit,
  parseTopicList,
  sendToUnfetchedFields,
  sendToUnfetchedGuard,
} from "@/lib/item-edit";
import { unfetchedDeleteGuard } from "@/lib/unfetched";
import {
  bulkAddTopics,
  bulkRemoveTopics,
  bulkSetSubject,
  changedRows,
  parseItemIds,
  parseTargetLabel,
  remapGuard,
  remapSubjects,
  remapTopics,
  withUniqueTopics,
  type OrganizeItem,
} from "@/lib/organize";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

function revalidateCorpus() {
  revalidatePath("/");
  revalidatePath("/unread");
  revalidatePath("/topics");
  revalidatePath("/all");
  revalidatePath("/organize");
}

function asOrganize(
  rows: Array<Pick<ItemRow, "id" | "subject" | "topics" | "ingest_status">>,
): OrganizeItem[] {
  return rows.map((row) => ({
    id: row.id,
    subject: row.subject,
    topics: row.topics ?? [],
    ingest_status: row.ingest_status ?? "",
  }));
}

async function persistOrganizeRows(
  db: ReturnType<typeof supabaseAdmin>,
  rows: OrganizeItem[],
): Promise<string | null> {
  for (const row of rows) {
    const { error } = await db
      .from("items")
      .update({ subject: row.subject, topics: row.topics })
      .eq("id", row.id)
      .eq("ingest_status", "ready");
    if (error) {
      return "Could not save edits.";
    }
  }
  return null;
}

export async function setReadState(itemId: number, read: boolean) {
  const db = supabaseAdmin();
  const { error } = await db
    .from("items")
    .update({ read_at: read ? new Date().toISOString() : null })
    .eq("id", itemId);
  if (error) {
    throw new Error(error.message);
  }
  revalidateCorpus();
}

export type UpdateItemMetadataState =
  | { ok: true; saved: boolean }
  | { ok: false; error: string };

export async function updateItemMetadata(
  itemId: number,
  _previousState: UpdateItemMetadataState,
  formData: FormData,
): Promise<UpdateItemMetadataState> {
  if (!Number.isInteger(itemId) || itemId <= 0) {
    return { ok: false, error: "Invalid article." };
  }

  const parsed = parseItemEdit({
    title: String(formData.get("title") || ""),
    snapshot: String(formData.get("snapshot") || ""),
    subject: String(formData.get("subject") || ""),
    topics: String(formData.get("topics") || ""),
  });
  if (!parsed.ok) {
    return parsed;
  }

  const db = supabaseAdmin();
  const { data: row, error: readError } = await db
    .from("items")
    .select("id, ingest_status")
    .eq("id", itemId)
    .maybeSingle();
  if (readError) {
    return { ok: false, error: "Could not save edits." };
  }
  const blocked = itemEditGuard(
    row ? { ingest_status: String(row.ingest_status) } : null,
  );
  if (blocked) {
    return { ok: false, error: blocked };
  }

  const { error } = await db
    .from("items")
    .update({
      title: parsed.fields.title,
      snapshot: parsed.fields.snapshot,
      subject: parsed.fields.subject,
      topics: parsed.fields.topics,
    })
    .eq("id", itemId)
    .eq("ingest_status", "ready");
  if (error) {
    return { ok: false, error: "Could not save edits." };
  }
  revalidateCorpus();
  return { ok: true, saved: true };
}

export type SendToUnfetchedState =
  | { ok: true; sent: boolean }
  | { ok: false; error: string };

export async function sendItemToUnfetched(
  itemId: number,
  _previousState: SendToUnfetchedState,
  _formData: FormData,
): Promise<SendToUnfetchedState> {
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
    return { ok: false, error: "Could not send to Unfetched." };
  }
  const blocked = sendToUnfetchedGuard(
    row ? { ingest_status: String(row.ingest_status) } : null,
  );
  if (blocked) {
    return { ok: false, error: blocked };
  }

  const { error } = await db
    .from("items")
    .update(sendToUnfetchedFields())
    .eq("id", itemId)
    .eq("ingest_status", "ready");
  if (error) {
    return { ok: false, error: "Could not send to Unfetched." };
  }

  await db.from("daily_picks").delete().eq("item_id", itemId);

  revalidateCorpus();
  revalidatePath("/unfetched");
  redirect("/unfetched");
}

const MAX_PDF_BYTES = 3.5 * 1024 * 1024;

export type SubmitArticleBodyState =
  | { ok: true; saved: boolean }
  | { ok: false; error: string };

export async function submitArticleBody(
  itemId: number,
  _previousState: SubmitArticleBodyState,
  formData: FormData,
): Promise<SubmitArticleBodyState> {
  if (!Number.isInteger(itemId) || itemId <= 0) {
    return { ok: false, error: "Invalid article." };
  }

  const db = supabaseAdmin();
  let body = String(formData.get("body") || "").trim();
  const pdf = formData.get("pdf");
  if (!body && pdf instanceof File && pdf.size > 0) {
    if (pdf.type !== "application/pdf") {
      return { ok: false, error: "Upload a PDF file." };
    }
    if (pdf.size > MAX_PDF_BYTES) {
      return { ok: false, error: "PDF must be under 3.5 MB." };
    }
    try {
      const { extractPdfText } = await import("@/lib/pdf");
      body = (await extractPdfText(pdf)).trim();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "unknown error";
      return { ok: false, error: `Could not extract PDF text: ${detail}` };
    }
  }
  if (!body) {
    return {
      ok: false,
      error: "Paste article text or upload a PDF with extractable text.",
    };
  }

  const { data: row, error: readError } = await db
    .from("items")
    .select("id, ingest_status")
    .eq("id", itemId)
    .maybeSingle();
  if (readError) {
    throw new Error(readError.message);
  }
  if (!row || row.ingest_status !== "pending_body") {
    return { ok: false, error: "Item is not awaiting a body." };
  }

  const { error } = await db
    .from("items")
    .update({ extracted_text: body })
    .eq("id", itemId)
    .eq("ingest_status", "pending_body");
  if (error) {
    throw new Error(error.message);
  }
  revalidatePath("/unfetched");
  return { ok: true, saved: true };
}

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

export type OrganizeState =
  | { ok: true; saved: boolean; updated: number }
  | { ok: false; error: string };

async function loadReadyItems(): Promise<
  { ok: true; items: OrganizeItem[] } | { ok: false; error: string }
> {
  const db = supabaseAdmin();
  const { data, error } = await db
    .from("items")
    .select("id, subject, topics, ingest_status")
    .eq("ingest_status", "ready");
  if (error) {
    return { ok: false, error: "Could not save edits." };
  }
  return { ok: true, items: asOrganize((data || []) as ItemRow[]) };
}

export async function remapVocabulary(
  _previousState: OrganizeState,
  formData: FormData,
): Promise<OrganizeState> {
  const kind = String(formData.get("kind") || "");
  const from = String(formData.get("from") || "");
  if (kind !== "subject" && kind !== "topic") {
    return { ok: false, error: "Invalid label type." };
  }
  const parsed = parseTargetLabel(String(formData.get("to") || ""));
  if (!parsed.ok) {
    return parsed;
  }
  const blocked = remapGuard(from, parsed.label);
  if (blocked) {
    return { ok: false, error: blocked };
  }

  const loaded = await loadReadyItems();
  if (!loaded.ok) {
    return loaded;
  }
  const cleaned = withUniqueTopics(loaded.items);
  const next =
    kind === "subject"
      ? remapSubjects(cleaned, from, parsed.label)
      : remapTopics(cleaned, from, parsed.label);
  const changed = changedRows(loaded.items, next);
  const persistError = await persistOrganizeRows(supabaseAdmin(), changed);
  if (persistError) {
    return { ok: false, error: persistError };
  }
  revalidateCorpus();
  return { ok: true, saved: true, updated: changed.length };
}

export async function bulkOrganize(
  _previousState: OrganizeState,
  formData: FormData,
): Promise<OrganizeState> {
  const op = String(formData.get("op") || "");
  const ids = parseItemIds(formData.get("ids"));
  if (!ids.ok) {
    return ids;
  }

  const loaded = await loadReadyItems();
  if (!loaded.ok) {
    return loaded;
  }
  const cleaned = withUniqueTopics(loaded.items);
  const byId = new Map(cleaned.map((item) => [item.id, item]));
  for (const id of ids.ids) {
    const blocked = itemEditGuard(byId.get(id) ?? null);
    if (blocked) {
      return { ok: false, error: blocked };
    }
  }

  let next = cleaned;
  if (op === "set-subject") {
    const parsed = parseTargetLabel(String(formData.get("subject") || ""));
    if (!parsed.ok) {
      return parsed;
    }
    next = bulkSetSubject(cleaned, ids.ids, parsed.label);
  } else if (op === "add-topics" || op === "remove-topics") {
    const tags = parseTopicList(String(formData.get("topics") || ""));
    if (tags.length === 0) {
      return { ok: false, error: "Name is required." };
    }
    next =
      op === "add-topics"
        ? bulkAddTopics(cleaned, ids.ids, tags)
        : bulkRemoveTopics(cleaned, ids.ids, tags);
  } else {
    return { ok: false, error: "Choose an action." };
  }

  const changed = changedRows(loaded.items, next);
  const persistError = await persistOrganizeRows(supabaseAdmin(), changed);
  if (persistError) {
    return { ok: false, error: persistError };
  }
  revalidateCorpus();
  return { ok: true, saved: true, updated: changed.length };
}

