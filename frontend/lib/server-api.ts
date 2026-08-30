/**
 * Server-side (route handler / middleware) helper for talking to Flask.
 *
 * API_BASE_URL points at the Flask app:
 * - dev: http://127.0.0.1:5000 (Flask dev server — 127.0.0.1 explicitly,
 *   because Node resolves `localhost` to ::1 first on Windows while Flask
 *   binds IPv4 only, which surfaces as ECONNRESET)
 * - prod: same-origin proxy or internal service URL (set in the env)
 */

export const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:5000";

export const REFRESH_COOKIE = "sp_refresh";

/** Cookie attributes: httpOnly + SameSite=Lax; Secure only over HTTPS so
 * plain-HTTP local dev still works. 30 days = REFRESH_TTL_DAYS on the
 * backend. */
export const REFRESH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60;

export function refreshCookieOptions(requestUrl: string) {
  const isHttps = requestUrl.startsWith("https://");
  return {
    httpOnly: true as const,
    sameSite: "lax" as const,
    secure: isHttps,
    path: "/",
    maxAge: REFRESH_COOKIE_MAX_AGE,
  };
}

/** Forward a JSON request to Flask and return (response, body). */
export async function flaskJson(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<{ response: Response; body: unknown }> {
  const { json, headers, ...rest } = init;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: { "Content-Type": "application/json", ...(headers as Record<string, string> | undefined) },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    cache: "no-store",
  });
  let body: unknown = null;
  if (response.status !== 204) {
    try {
      body = await response.json();
    } catch {
      body = null;
    }
  }
  return { response, body };
}
