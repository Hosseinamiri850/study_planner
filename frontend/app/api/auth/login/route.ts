import { NextResponse, type NextRequest } from "next/server";

import { flaskJson, refreshCookieOptions, REFRESH_COOKIE } from "@/lib/server-api";

/** POST /api/auth/login — proxy to Flask, stash the refresh token in an
 * httpOnly cookie, hand the access token + user to the client. The
 * refresh token is STRIPPED from the JSON body: it must never be readable
 * by client-side JavaScript (XSS would otherwise lift the long-lived
 * token straight out of the response). */
export async function POST(request: NextRequest) {
  const payload = await request.json().catch(() => ({}));
  const { response, body } = await flaskJson("/api/auth/login", { method: "POST", json: payload });
  if (!response.ok) return NextResponse.json(body, { status: response.status });

  const data = body as { refresh_token: string; [key: string]: unknown };
  const nextResponse = NextResponse.json(body, { status: response.status });
  nextResponse.cookies.set(REFRESH_COOKIE, data.refresh_token, refreshCookieOptions(request.url));
  const { refresh_token: _removed, ...clientBody } = data;
  return new NextResponse(JSON.stringify(clientBody), {
    status: response.status,
    headers: nextResponse.headers,
  });
}
