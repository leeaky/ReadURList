"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { supabaseAdmin } from "@/lib/supabase";
import {
  itemEditGuard,
  parseItemEdit,
  sendToUnfetchedFields,
  sendToUnfetchedGuard,
} from "@/lib/item-edit";
import { unfetchedDeleteGuard } from "@/lib/unfetched";

export async function setReadState(itemId: number, read: boolean) {
  const db = supabaseAdmin();
  const { error } = await db
    .from("items")
    .update({ read_at: read ? new Date().toISOString() : null })
    .eq("id", itemId);
  if (error) {
    throw new Error(error.message);
  }
  revalidatePath("/");
  revalidatePath("/unread");
  revalidatePath("/topics");
  revalidatePath("/clusters");
  revalidatePath("/all");
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
  revalidatePath("/");
  revalidatePath("/unread");
  revalidatePath("/topics");
  revalidatePath("/clusters");
  revalidatePath("/all");
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

  revalidatePath("/");
  revalidatePath("/unread");
  revalidatePath("/topics");
  revalidatePath("/clusters");
  revalidatePath("/all");
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
