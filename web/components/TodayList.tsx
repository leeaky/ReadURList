"use client";

import Link from "next/link";
import { ItemCard } from "./ItemCard";
import { useFilters } from "./AppFrame";
import { itemMatchesFilter } from "@/lib/filters";
import { fallenOffWords, pointsLine, readingTime, reasonWords, splitSections } from "@/lib/today";
import type { ItemRow } from "@/lib/supabase";

export type TodayPick = {
  item: ItemRow;
  reason: string;
  rank: number;
  section: string | null;
  subjectPoints: number | null;
  recencyPoints: number | null;
};

export type FallenOff = {
  itemId: number;
  url: string;
  title: string;
  cause: string;
  pointsBefore: number;
  pointsAfter: number | null;
};

export function TodayList({
  picks,
  fallen,
  waitingOnUnfetched,
  subjects,
}: {
  picks: TodayPick[];
  fallen: FallenOff[];
  waitingOnUnfetched: number;
  subjects: string[];
}) {
  const filters = useFilters();
  const visible = picks.filter((pick) => itemMatchesFilter(pick.item, filters));

  if (picks.length === 0) {
    return (
      <p className="empty">
        No ranked picks yet. Run the daily job (`readurlist-digest` or /digest).
      </p>
    );
  }
  const { short, long } = splitSections(visible);

  function cards(rows: TodayPick[]) {
    return (
      <div className="article-list">
        {rows.map((pick) => (
          <ItemCard
            key={pick.item.id}
            item={pick.item}
            reason={reasonWords(pick.reason)}
            points={pointsLine(pick.subjectPoints, pick.recencyPoints)}
            readTime={readingTime(pick.item.word_count)}
            rank={pick.rank}
            subjects={subjects}
          />
        ))}
      </div>
    );
  }

  return (
    <>
      {visible.length === 0 ? <p className="empty">No articles match your filters.</p> : null}
      <section className="today-section">
        <h2 className="today-heading">Short reads</h2>
        {short.length > 0 ? cards(short) : <p className="empty">No short reads match.</p>}
      </section>
      <section className="today-section">
        <h2 className="today-heading">Long read</h2>
        {long.length > 0 ? (
          cards(long)
        ) : (
          <p className="empty">
            No long read ready. {waitingOnUnfetched} papers are waiting on{" "}
            <Link href="/unfetched">Unfetched</Link>.
          </p>
        )}
      </section>
      {fallen.length > 0 ? (
        <section className="today-section today-fallen">
          <h2 className="today-heading">Fallen off since the last list</h2>
          <ul className="fallen-list">
            {fallen.map((row) => {
              const words = fallenOffWords({
                cause: row.cause,
                points_before: row.pointsBefore,
                points_after: row.pointsAfter,
              });
              return (
                <li key={row.itemId}>
                  <a href={row.url} target="_blank" rel="noopener noreferrer">
                    {row.title || row.url}
                  </a>
                  <span className="text-muted">
                    {" "}
                    — {words.cause} · {words.points}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
    </>
  );
}
