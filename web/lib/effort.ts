// Effort label (build map stage 4), same rule as the worker's
// src/readurlist/effort.py: about 230 words a minute; short is under 15 minutes.
import type { FilterStatus } from "./filters.ts";

export const WORDS_PER_MINUTE = 230;
const SHORT_UNDER_MINUTES = 15;

export type Length = "short" | "long";

export function readingMinutes(words: number): number {
  return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

export function effortOf(words: number | null | undefined): Length | null {
  if (words == null) return null;
  return words / WORDS_PER_MINUTE < SHORT_UNDER_MINUTES ? "short" : "long";
}

export function effortLabel(words: number | null | undefined): string | null {
  const effort = effortOf(words);
  if (effort == null || words == null) return null;
  return `${effort === "short" ? "Short" : "Long"} · ${readingMinutes(words)} min`;
}

// No word count counts as short, as in the day's list (stage 6).
export function matchesLength(item: { word_count?: number | null }, length: Length | null): boolean {
  if (length == null) return true;
  return (effortOf(item.word_count) ?? "short") === length;
}

export function lengthFromParam(value: string | undefined): Length | null {
  return value === "short" || value === "long" ? value : null;
}

export function allHref(status: FilterStatus, length: Length | null): string {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (length) params.set("length", length);
  const query = params.toString();
  return query ? `/all?${query}` : "/all";
}
