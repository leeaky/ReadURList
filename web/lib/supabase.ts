import { createClient } from "@supabase/supabase-js";

export function supabaseAdmin() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set");
  }
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export type ItemRow = {
  id: number;
  url: string;
  title: string;
  snapshot: string;
  subject: string;
  topics: string[] | null;
  keywords: string[] | null;
  created_at: string;
  read_at: string | null;
  skipped_at?: string | null;
  ingest_status?: string;
  extracted_text?: string | null;
  note?: string | null;
  word_count?: number | null;
};

export type DailyPickRow = {
  run_on: string;
  item_id: number;
  rank: number;
  score: number;
  reason: string;
  section?: string | null;
  subject_points?: number | null;
  recency_points?: number | null;
  items: ItemRow | ItemRow[] | null;
};

export type FallenOffRow = {
  item_id: number;
  cause: string;
  points_before: number;
  points_after: number | null;
  items: Pick<ItemRow, "url" | "title"> | Pick<ItemRow, "url" | "title">[] | null;
};
