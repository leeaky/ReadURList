import Link from "next/link";
import { login } from "./actions";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; next?: string }>;
}) {
  const params = await searchParams;
  return (
    <main className="page">
      <header className="brand">
        <div>
          <h1>ReadURList</h1>
          <p className="tagline">Personal corpus — sign in.</p>
        </div>
      </header>
      <form className="login-form" action={login}>
        <input type="hidden" name="next" value={params.next || "/"} />
        <label>
          Password
          <input type="password" name="password" autoFocus required />
        </label>
        {params.error ? <p className="error">Wrong password.</p> : null}
        <button type="submit">Enter</button>
      </form>
      <p className="empty">
        <Link href="/">Home</Link>
      </p>
    </main>
  );
}
