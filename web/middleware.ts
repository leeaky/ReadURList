import { NextRequest, NextResponse } from "next/server";
import { AUTH_COOKIE, siteToken } from "./lib/auth";

export async function middleware(request: NextRequest) {
  const password = process.env.SITE_PASSWORD;
  if (!password) {
    return new NextResponse("SITE_PASSWORD is not configured", { status: 500 });
  }
  const expected = await siteToken(password);
  const cookie = request.cookies.get(AUTH_COOKIE)?.value;
  if (cookie === expected) {
    return NextResponse.next();
  }
  const login = new URL("/login", request.url);
  login.searchParams.set("next", request.nextUrl.pathname);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/((?!login|_next/static|_next/image|favicon.ico).*)"],
};
