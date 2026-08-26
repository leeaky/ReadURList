import Link from "next/link";
import { setReadState } from "@/app/actions";
import type { ItemRow } from "@/lib/supabase";

function formatWhen(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().slice(0, 16).replace("T", " ");
}

export function ItemCard({
  item,
  reason,
}: {
  item: ItemRow;
  reason?: string;
}) {
  const read = Boolean(item.read_at);
  const toggle = setReadState.bind(null, item.id, !read);
  const topics = item.topics ?? [];
  return (
    <article className="item">
      <a className="item-title" href={item.url} target="_blank" rel="noopener noreferrer">
        {item.title || item.url}
      </a>
      {item.snapshot ? <p className="item-summary">{item.snapshot}</p> : null}
      {reason ? <p className="item-reason">Why: {reason}</p> : null}
      {item.similar_to_item_id ? (
        <p className="item-note">Possible duplicate of item #{item.similar_to_item_id}</p>
      ) : null}
      <div className="chips">
        {item.subject ? <span className="chip">{item.subject}</span> : null}
        {topics.slice(0, 8).map((t) => (
          <span className="chip" key={t}>
            {t}
          </span>
        ))}
      </div>
      <div className="item-meta">
        <a href={item.url} target="_blank" rel="noopener noreferrer">
          {item.url}
        </a>
        <time dateTime={item.created_at}>{formatWhen(item.created_at)}</time>
        {read ? <span>Read {formatWhen(item.read_at)}</span> : <span>Unread</span>}
        <form action={toggle}>
          <button type="submit" className={read ? "ghost" : undefined}>
            {read ? "Mark unread" : "Mark read"}
          </button>
        </form>
      </div>
    </article>
  );
}

export function Nav({ current }: { current: string }) {
  const tabs = [
    ["/", "Today"],
    ["/unread", "Unread"],
    ["/topics", "Topics"],
    ["/clusters", "Clusters"],
    ["/all", "All"],
  ] as const;
  return (
    <nav className="tabs" aria-label="Views">
      {tabs.map(([href, label]) => (
        <Link key={href} href={href} aria-current={current === href ? "page" : undefined}>
          {label}
        </Link>
      ))}
    </nav>
  );
}

export function Brand({ tagline }: { tagline: string }) {
  return (
    <header className="brand">
      <Link href="/" className="brand-lockup">
        <img
          className="brand-logo"
          src="/logo.png"
          alt=""
          width={640}
          height={640}
        />
        <div>
          <h1>ReadURList</h1>
          <p className="tagline">{tagline}</p>
        </div>
      </Link>
    </header>
  );
}

export function Shell({
  current,
  children,
}: {
  current: string;
  children: React.ReactNode;
}) {
  return (
    <main className="page">
      <Brand tagline="Capture in Telegram. Reorganize here." />
      <Nav current={current} />
      {children}
    </main>
  );
}
