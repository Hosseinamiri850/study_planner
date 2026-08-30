import { NextResponse, type NextRequest } from "next/server";

import { API_BASE_URL } from "@/lib/server-api";

/** Catch-all proxy: forwards browser API calls (except /api/auth/*, which
 * has dedicated handlers) to Flask, passing the client's Authorization
 * header through. Keeps the SPA same-origin — no CORS anywhere — and the
 * Bearer access token still travels client-side (the proxy never stores
 * it). Method + body + status are preserved 1:1 with Flask. */

const FORWARD_HEADERS = ["authorization", "content-type", "accept"];

async function proxy(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const url = new URL(request.url);
  const target = `${API_BASE_URL}/api/${path.join("/")}${url.search}`;

  const headers = new Headers();
  for (const name of FORWARD_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const method = request.method;
  const hasBody = method !== "GET" && method !== "HEAD";
  const response = await fetch(target, {
    method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
  });

  // Strip hop-by-hop/response-only headers; keep the JSON body as-is.
  const responseHeaders = new Headers();
  const contentType = response.headers.get("content-type");
  if (contentType) responseHeaders.set("content-type", contentType);
  return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
