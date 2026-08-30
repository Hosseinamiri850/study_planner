import { NextResponse, type NextRequest } from "next/server";

import { flaskJson, refreshCookieOptions, REFRESH_COOKIE } from "@/lib/server-api";

/** POST /api/auth/logout — revoke the refresh token server-side (ownership
 * check happens in Flask: this proxy cannot read the access token, so it
 * forwards the presented refresh token from the cookie; Flask only revokes
 * it if it belongs to the authenticated caller of the Bearer request).
 *
 * Here the proxy has no Bearer token — Flask's /api/auth/logout requires
 * one. So the handler asks the client... no: revocation without an access
 * token cannot be ownership-verified. Instead this route REQUIRES the
 * client to send its (short-lived) access token in the Authorization
 * header; the client always has it at logout time. */
export async function POST(request: NextRequest) {
  const authorization = request.headers.get("Authorization");
  const token = request.cookies.get(REFRESH_COOKIE)?.value;

  // Always clear the cookie, even if Flask revocation fails — the client
  // is logging out regardless and a stale cookie is worse than none.
  const nextResponse = new NextResponse(null, { status: 204 });
  nextResponse.cookies.set(REFRESH_COOKIE, "", { ...refreshCookieOptions(request.url), maxAge: 0 });

  if (authorization && token) {
    try {
      await flaskJson("/api/auth/logout", {
        method: "POST",
        json: { refresh_token: token },
        headers: { Authorization: authorization },
      });
    } catch {
      // network failure: cookie already cleared client-side; the refresh
      // token's own 30-day TTL bounds any residual risk.
    }
  }
  return nextResponse;
}
