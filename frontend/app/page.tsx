"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth-context";

/** Root: send authenticated users to the app, others to login. Matches
 * the backend's `/` redirect behavior (web.home). */
export default function HomeRedirect() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/app");
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  return null;
}
