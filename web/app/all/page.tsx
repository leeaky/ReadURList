import { AppFrame } from "@/components/AppFrame";
import { AllList } from "@/components/AllList";
import { fetchReadyCorpus } from "@/lib/fetch-corpus";
import { subjectsFromItems, type FilterStatus } from "@/lib/filters";

export const dynamic = "force-dynamic";

function statusFromParams(params: { status?: string; filter?: string }): FilterStatus {
  const value = params.status || params.filter;
  if (value === "unread" || value === "read" || value === "skipped" || value === "stale") {
    return value;
  }
  return null;
}

export default async function AllPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; filter?: string }>;
}) {
  const params = await searchParams;
  const items = await fetchReadyCorpus();
  const subjects = subjectsFromItems(items).map((row) => row.name);
  return (
    <AppFrame
      current="/all"
      showSidebar
      facetItems={items}
      initialStatus={statusFromParams(params)}
    >
      <AllList items={items} subjects={subjects} />
    </AppFrame>
  );
}
