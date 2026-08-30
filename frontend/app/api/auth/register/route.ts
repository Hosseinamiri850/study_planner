import { NextResponse, type NextRequest } from "next/server";

import { flaskJson, refreshCookieOptions, REFRESH_COOKIE } from "@/lib/server-api";

/** POST /api/auth/register — proxy to Flask; refresh token goes straight
 * into the httpOnly cookie (the user is logged in on registration). */
export async function POST(request: NextRequest) {
  const payload = await request.json().catch(() => ({}));
  const { response, body } = await flaskJson("/api/auth/register", { method: "POST", json: payload });
  if (!response.ok) return NextResponse.json(body, { status: response.status });

  const data = body as { refresh_token: string };
  const nextResponse = NextResponse.json(body, { status: response.status });
  nextResponse.cookies.set(REFRESH_COOKIE, data.refresh_token, refreshCookieOptions(request.url));
  return nextResponse;
}
