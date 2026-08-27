import Link from "next/link";

export { ItemCard } from "./ItemCard";

export function Nav({ current }: { current: string }) {
  const tabs = [
    ["/", "Today"],
    ["/unread", "Unread"],
    ["/topics", "Topics"],
    ["/clusters", "Clusters"],
    ["/all", "All"],
    ["/unfetched", "Unfetched"],
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
