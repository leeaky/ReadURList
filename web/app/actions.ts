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

export async function submitArticleBody(itemId: number, formData: FormData) {
  const db = supabaseAdmin();
  let body = String(formData.get("body") || "").trim();
  const pdf = formData.get("pdf");
  if (!body && pdf instanceof File && pdf.size > 0) {
    if (pdf.size > MAX_PDF_BYTES) {
      throw new Error("PDF must be under 3.5 MB.");
    }
    const { extractPdfText } = await import("@/lib/pdf");
    body = (await extractPdfText(pdf)).trim();
  }
  if (!body) {
    throw new Error("Paste article text or upload a PDF with extractable text.");
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
    throw new Error("Item is not awaiting a body.");
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
}
