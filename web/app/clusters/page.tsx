import { ItemCard, Shell } from "@/components/ui";
import { isReadyItem } from "@/lib/item-edit";
import { CLUSTERS_BLURB } from "@/lib/ranking-copy";
import { supabaseAdmin, type ClusterRow, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function ClustersPage() {
  const db = supabaseAdmin();
  const clusters = await db
    .from("clusters")
    .select("id, label, computed_at")
    .order("computed_at", { ascending: false });
  if (clusters.error) {
    throw new Error(clusters.error.message);
  }
  const rows = (clusters.data || []) as ClusterRow[];
  // Latest run only: groups share computed_at from the last job.
  const latest = rows[0]?.computed_at;
  const latestClusters = latest
    ? rows.filter((c) => c.computed_at === latest)
    : [];

  const blocks: { cluster: ClusterRow; items: ItemRow[] }[] = [];
  for (const cluster of latestClusters) {
    const members = await db
      .from("cluster_items")
      .select("item_id, items(*)")
      .eq("cluster_id", cluster.id);
    if (members.error) {
      throw new Error(members.error.message);
    }
    const items = (members.data || [])
      .map((row: { items: ItemRow | ItemRow[] | null }) => {
        const value = row.items;
        return Array.isArray(value) ? value[0] : value;
      })
      .filter((item): item is ItemRow => Boolean(item) && isReadyItem(item));
    blocks.push({ cluster, items });
  }

  return (
    <Shell current="/clusters">
      <p className="empty">{CLUSTERS_BLURB}</p>
      {blocks.length === 0 ? (
        <p className="empty">No clusters yet. Run the daily job on the NUC.</p>
      ) : (
        blocks.map(({ cluster, items }) => (
          <section className="cluster-block" key={cluster.id}>
            <h2>{cluster.label}</h2>
            <p className="empty">{items.length} article(s)</p>
            {items.map((item) => (
              <ItemCard key={item.id} item={item} />
            ))}
          </section>
        ))
      )}
    </Shell>
  );
}
