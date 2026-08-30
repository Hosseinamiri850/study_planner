"use client";

/**
 * Authentication state for the SPA.
 *
 * Token model (matches the backend contract and the migration plan):
 * - Access token: in memory only (React state). 15-minute TTL, never
 *   persisted — XSS exposure window is one tab lifetime.
 * - Refresh token: httpOnly cookie owned by the Next route handlers under
 *   app/api/auth/*; JavaScript never reads or writes it.
 * - On mount the provider silently refreshes to restore the session, so a
 *   page reload re-authenticates without user interaction.
 * - On a 401 from any API call, authFetch transparently refreshes ONCE and
 *   retries; a failed refresh clears the user and redirects to /login.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import { ApiClient } from "./api";
import { ApiError } from "./errors";
import type { MeUser } from "@/types/api";

interface AuthState {
  user: MeUser | null;
  /** Null while the initial silent refresh is in flight. */
  status: "loading" | "authenticated" | "unauthenticated";
  api: ApiClient;
  logout: () => Promise<void>;
  /** Adopt the identity returned by login/register (sets user + token). */
  signIn: (user: MeUser, accessToken: string) => void;
  /** Store the access token before /api/me is callable (login flow). */
  setToken: (token: string) => void;
  /** Re-pull /api/me into state (after profile edits). */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeUser | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const accessToken = useRef<string | null>(null);
  const refreshing = useRef<Promise<boolean> | null>(null);
  const router = useRouter();

  const resetSession = useCallback(() => {
    accessToken.current = null;
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  /** POST /api/auth/refresh — the route handler uses the httpOnly cookie.
   * Returns true when a new access token was obtained. Serialized so
   * concurrent 401s share one refresh. */
  const refreshSession = useCallback(async (): Promise<boolean> => {
    if (refreshing.current) return refreshing.current;
    const attempt = (async () => {
      try {
        const response = await fetch("/api/auth/refresh", { method: "POST" });
        if (!response.ok) return false;
        const data = (await response.json()) as { access_token: string };
        accessToken.current = data.access_token;
        return true;
      } catch {
        return false;
      }
    })();
    refreshing.current = attempt;
    const ok = await attempt;
    refreshing.current = null;
    return ok;
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await refreshSession();
      if (cancelled) return;
      if (!ok) {
        resetSession();
        return;
      }
      try {
        const response = await fetch("/api/proxy/me", {
          headers: { Authorization: `Bearer ${accessToken.current}` },
        });
        if (!response.ok) throw new ApiError(response.status, "");
        const data = (await response.json()) as { user: MeUser };
        setUser(data.user);
        setStatus("authenticated");
      } catch {
        resetSession();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshSession, resetSession]);

  const authFetch = useCallback(
    async (path: string, init?: RequestInit): Promise<Response> => {
      const doFetch = () => {
        const headers = new Headers(init?.headers);
        if (accessToken.current) headers.set("Authorization", `Bearer ${accessToken.current}`);
        return fetch(path, { ...init, headers });
      };
      let response = await doFetch();
      if (response.status === 401 && accessToken.current) {
        const ok = await refreshSession();
        if (ok) {
          response = await doFetch();
        } else {
          resetSession();
          router.replace("/login");
          throw new ApiError(401, "Your session has expired. Please sign in again.");
        }
      }
      return response;
    },
    [refreshSession, resetSession, router],
  );

  const api = useMemo(() => new ApiClient(authFetch), [authFetch]);

  const signIn = useCallback(
    (nextUser: MeUser, token: string) => {
      accessToken.current = token;
      setUser(nextUser);
      setStatus("authenticated");
    },
    [],
  );

  const setToken = useCallback((token: string) => {
    accessToken.current = token;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // best-effort: clear the client regardless
    }
    accessToken.current = null;
    setUser(null);
    setStatus("unauthenticated");
    router.replace("/login");
  }, [api, router]);

  const refreshUser = useCallback(async () => {
    if (!accessToken.current) return;
    const response = await fetch("/api/proxy/me", {
      headers: { Authorization: `Bearer ${accessToken.current}` },
    });
    if (response.ok) {
      const data = (await response.json()) as { user: MeUser };
      setUser(data.user);
    }
  }, []);

  const value = useMemo(
    () => ({ user, status, api, logout, signIn, setToken, refreshUser }),
    [user, status, api, logout, signIn, setToken, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) throw new Error("useAuth must be used inside <AuthProvider>.");
  return state;
}
