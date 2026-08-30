import { NextResponse, type NextRequest } from "next/server";

import { REFRESH_COOKIE } from "@/lib/server-api";

/** Coarse route gating: presence of the httpOnly refresh cookie decides
 * whether /app/* is even attempted and whether authed users skip the
 * login/register pages. This is UX routing, NOT a security boundary — the
 * API enforces authorization; pages also gate on the /api/me-derived user
 * via <RequireAuth>. */
export function middleware(request: NextRequest) {
  const hasSession = request.cookies.has(REFRESH_COOKIE);
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/app") && !hasSession) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    return NextResponse.redirect(login);
  }

  if ((pathname === "/login" || pathname === "/register") && hasSession) {
    return NextResponse.redirect(new URL("/app", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*", "/login", "/register"],
};
