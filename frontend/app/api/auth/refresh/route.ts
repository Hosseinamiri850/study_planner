import { NextResponse, type NextRequest } from "next/server";

import { flaskJson, refreshCookieOptions, REFRESH_COOKIE } from "@/lib/server-api";

/** POST /api/auth/refresh — exchange the httpOnly refresh cookie for a new
 * token pair. Flask rotates (revokes the presented token), so the rotated
 * refresh token must replace the cookie atomically with this response. */
export async function POST(request: NextRequest) {
  const token = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "No refresh token." }, { status: 401 });

  const { response, body } = await flaskJson("/api/auth/refresh", {
    method: "POST",
    json: { refresh_token: token },
  });
  if (!response.ok) {
    // Invalid/expired/revoked refresh token — drop the dead cookie so the
    // client stops retrying with it.
    const nextResponse = NextResponse.json(body, { status: response.status });
    nextResponse.cookies.set(REFRESH_COOKIE, "", { ...refreshCookieOptions(request.url), maxAge: 0 });
    return nextResponse;
  }

  const data = body as { refresh_token: string };
  const nextResponse = NextResponse.json(body, { status: 200 });
  nextResponse.cookies.set(REFRESH_COOKIE, data.refresh_token, refreshCookieOptions(request.url));
  return nextResponse;
}
