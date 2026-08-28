import Link from "next/link";

export function BrandLockup({ tagline }: { tagline: string }) {
  return (
    <Link href="/" className="brand-lockup">
      <img
        className="brand-mark"
        src="/logo.png"
        alt=""
        width={32}
        height={32}
      />
      <span className="brand-text">
        <span className="nav-brand">ReadURList</span>
        <span className="text-muted brand-tagline">{tagline}</span>
      </span>
    </Link>
  );
}

export function Brand({ tagline }: { tagline: string }) {
  return (
    <header>
      <BrandLockup tagline={tagline} />
    </header>
  );
}
