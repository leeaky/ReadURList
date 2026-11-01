// Today page wording (build map stage 7). Reading time matches the worker's
// effort rule: about 230 words a minute (src/readurlist/effort.py).
const WORDS_PER_MINUTE = 230;

export function readingTime(words: number | null | undefined): string | null {
  if (words == null) return null;
  return `${Math.max(1, Math.round(words / WORDS_PER_MINUTE))} min read`;
}

export function reasonWords(reason: string): string {
  return reason.replace(/\s*\(subject \d+ \+ recency \d+ = \d+\)\s*$/, "");
}

export function pointsLine(
  subject: number | null | undefined,
  recency: number | null | undefined,
): string | null {
  if (subject == null || recency == null) return null;
  return `subject ${subject} + recency ${recency} = ${subject + recency} points`;
}

export function splitSections<T extends { section?: string | null }>(picks: T[]) {
  return {
    short: picks.filter((p) => (p.section ?? "short") !== "long"),
    long: picks.filter((p) => p.section === "long"),
  };
}

const FALL_CAUSES: Record<string, string> = {
  read: "you read it",
  skipped: "you skipped it",
  outscored: "outscored by newer saves",
  subject_full: "its subject already has two picks",
  gone: "no longer in the pile",
};

export function fallenOffWords(row: {
  cause: string;
  points_before: number;
  points_after: number | null;
}): { cause: string; points: string } {
  const before = Math.round(row.points_before);
  return {
    cause: FALL_CAUSES[row.cause] ?? row.cause,
    points:
      row.points_after == null
        ? `was ${before} points`
        : `${before} → ${row.points_after} points`,
  };
}
