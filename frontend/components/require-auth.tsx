"use client";

/** Page-level auth gate (the real complement to middleware.ts): while the
 * silent refresh is pending show a spinner; unauthenticated users are
 * redirected. Rendering the guarded children only in the authenticated
 * state keeps API calls off the screen until the token exists.
 *
 * Reads `?next=` from window.location instead of useSearchParams so
 * prerendering does not require a Suspense boundary around every usage. */

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth-context";
import { Spinner } from "./ui";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const [next, setNext] = useState("/app");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("next");
    setNext(requested && requested.startsWith("/") ? requested : "/app");
  }, []);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [status, router, next]);

  if (status !== "authenticated") {
    return <Spinner />;
  }
  return <>{children}</>;
}
