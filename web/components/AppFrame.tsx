"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  subjectsFromItems,
  tagsFromItems,
  type FilterStatus,
} from "@/lib/filters";
import { ThemeToggle } from "./ThemeToggle";
import { BrandLockup } from "./Brand";

export type FacetItem = { subject: string; topics: string[] | null };

type FilterContextValue = {
  search: string;
  setSearch: (q: string) => void;
  selectedSubjects: string[];
  selectedTags: string[];
  status: FilterStatus;
  toggleSubject: (name: string) => void;
  toggleTag: (tag: string) => void;
  clearFilters: () => void;
  hasFilters: boolean;
};

const FilterContext = createContext<FilterContextValue | null>(null);

export function useFilters(): FilterContextValue {
  const ctx = useContext(FilterContext);
  if (!ctx) {
    throw new Error("useFilters must be used within AppFrame");
  }
  return ctx;
}

function toggleIn(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

const TABS = [
  ["/", "Today"],
  ["/all", "All"],
  ["/organize", "Organize"],
  ["/unfetched", "Unfetched"],
] as const;

export function AppFrame({
  current,
  showSidebar,
  facetItems,
  initialStatus = null,
  children,
}: {
  current: string;
  showSidebar: boolean;
  facetItems: FacetItem[];
  initialStatus?: FilterStatus;
  children: ReactNode;
}) {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [status, setStatus] = useState<FilterStatus>(initialStatus);

  const toggleSubject = useCallback((name: string) => {
    setSelectedSubjects((prev) => toggleIn(prev, name));
  }, []);
  const toggleTag = useCallback((tag: string) => {
    setSelectedTags((prev) => toggleIn(prev, tag));
  }, []);
  const clearFilters = useCallback(() => {
    setSelectedSubjects([]);
    setSelectedTags([]);
    setStatus(null);
    if (current === "/all" && initialStatus) {
      router.replace("/all");
    }
  }, [current, initialStatus, router]);

  const hasFilters =
    search.trim().length > 0 ||
    selectedSubjects.length > 0 ||
    selectedTags.length > 0 ||
    status != null;

  const value = useMemo(
    () => ({
      search,
      setSearch,
      selectedSubjects,
      selectedTags,
      status,
      toggleSubject,
      toggleTag,
      clearFilters,
      hasFilters,
    }),
    [
      search,
      selectedSubjects,
      selectedTags,
      status,
      toggleSubject,
      toggleTag,
      clearFilters,
      hasFilters,
    ],
  );

  const [filtersOpen, setFiltersOpen] = useState(false);
  const subjects = subjectsFromItems(facetItems);
  const tags = tagsFromItems(facetItems);
  const facetCount =
    selectedSubjects.length + selectedTags.length + (status != null ? 1 : 0);

  return (
    <FilterContext.Provider value={value}>
      <header className="site-header">
        <div className="site-header-row">
          <BrandLockup tagline="Capture in Telegram. Reorganize here." />
          <div className="header-tools">
            <div className="search-wrap">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                className="input"
                type="search"
                placeholder="Search your list"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                aria-label="Search your list"
              />
            </div>
            <ThemeToggle />
          </div>
        </div>
        <nav className="tabs" aria-label="Views">
          {TABS.map(([href, label]) => (
            <Link key={href} href={href} aria-current={current === href ? "page" : undefined}>
              {label}
            </Link>
          ))}
        </nav>
      </header>
      <div className="site-body">
        {showSidebar ? (
          <aside className="sidebar">
            <button
              type="button"
              className="sidebar-toggle"
              aria-expanded={filtersOpen}
              aria-controls="sidebar-panel"
              onClick={() => setFiltersOpen((open) => !open)}
            >
              <span>
                Filters
                {facetCount > 0 ? ` (${facetCount})` : ""}
              </span>
              <svg
                className={filtersOpen ? "article-chevron is-open" : "article-chevron"}
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
            <div
              id="sidebar-panel"
              className={filtersOpen ? "sidebar-panel is-open" : "sidebar-panel"}
            >
              <div className="sidebar-label">Topics</div>
              <div className="topic-list">
                {subjects.map((row) => (
                  <button
                    key={row.name}
                    type="button"
                    className="topic-row"
                    aria-pressed={selectedSubjects.includes(row.name)}
                    onClick={() => toggleSubject(row.name)}
                  >
                    <span>{row.name}</span>
                    <span className="topic-count">{row.count}</span>
                  </button>
                ))}
              </div>
              <div className="sidebar-label">Tags</div>
              <div className="tag-cloud">
                {tags.map((row) => (
                  <button
                    key={row.tag}
                    type="button"
                    className={
                      selectedTags.includes(row.tag)
                        ? "tag tag-accent tag-button"
                        : "tag tag-outline tag-button"
                    }
                    aria-pressed={selectedTags.includes(row.tag)}
                    onClick={() => toggleTag(row.tag)}
                  >
                    {row.tag}
                  </button>
                ))}
              </div>
              {hasFilters && (selectedSubjects.length > 0 || selectedTags.length > 0 || status != null) ? (
                <button type="button" className="btn btn-ghost" onClick={clearFilters}>
                  Clear filters
                </button>
              ) : null}
            </div>
          </aside>
        ) : null}
        <div className="main-col">{children}</div>
      </div>
    </FilterContext.Provider>
  );
}
