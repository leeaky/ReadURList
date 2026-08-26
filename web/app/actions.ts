"use server";

import { revalidatePath } from "next/cache";
import { supabaseAdmin } from "@/lib/supabase";

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

const MAX_PDF_BYTES = 3.5 * 1024 * 1024;

export type SubmitArticleBodyState =
  | { ok: true }
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
  return { ok: true };
}
