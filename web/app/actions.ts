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
