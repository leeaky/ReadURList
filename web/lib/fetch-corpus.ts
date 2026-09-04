import { corpusPageRange, hasMoreCorpusPages, READY_CORPUS_SELECT } from "@/lib/corpus";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export async function fetchReadyCorpus(): Promise<ItemRow[]> {
  const db = supabaseAdmin();
  const rows: ItemRow[] = [];
  let page = 0;
  while (true) {
    const { from, to } = corpusPageRange(page);
    const { data, error } = await db
      .from("items")
      .select(READY_CORPUS_SELECT)
      .eq("ingest_status", "ready")
      .order("created_at", { ascending: false })
      .range(from, to);
    if (error) {
      throw new Error(error.message);
    }
    const batch = (data || []) as ItemRow[];
    rows.push(...batch);
    if (!hasMoreCorpusPages(batch.length)) {
      break;
    }
    page += 1;
  }
  return rows;
}
