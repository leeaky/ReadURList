import { AppFrame } from "@/components/AppFrame";
import { OrganizeView } from "@/components/OrganizeView";
import { fetchReadyCorpus } from "@/lib/fetch-corpus";

export const dynamic = "force-dynamic";

export default async function OrganizePage() {
  const items = await fetchReadyCorpus();
  return (
    <AppFrame current="/organize" showSidebar={false} facetItems={items}>
      <OrganizeView items={items} />
    </AppFrame>
  );
}
