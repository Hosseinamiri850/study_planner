"use client";

/** Persistent banner shown while a support agent is impersonating a user
 * (TASK-040). In-memory state — a reload ends the session, matching the
 * impersonation token's own expiry (no extension by design). */

import { useEffect, useState } from "react";
import { Eye, X } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { useLang } from "@/lib/lang-context";

/** TTL of the impersonation token: same as a normal access token. */
const TOKEN_TTL_MINUTES = 15;

export function ImpersonationBanner() {
  const { user, impersonating, endImpersonation } = useAuth();
  const { t } = useLang();
  const [minutesLeft, setMinutesLeft] = useState(TOKEN_TTL_MINUTES);

  useEffect(() => {
    if (!impersonating) return;
    setMinutesLeft(TOKEN_TTL_MINUTES);
    const timer = setInterval(() => {
      setMinutesLeft((m) => (m > 1 ? m - 1 : TOKEN_TTL_MINUTES));
    }, 60_000);
    return () => clearInterval(timer);
  }, [impersonating]);

  if (!impersonating || !user) return null;

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 border-b border-warning bg-warning/10 px-4 py-2"
    >
      <p className="flex items-center gap-2 text-sm font-medium text-text-primary">
        <Eye size={16} aria-hidden className="text-warning" />
        {t("support.banner_viewing", { username: user.username, minutes: minutesLeft })}
      </p>
      <button
        type="button"
        onClick={endImpersonation}
        className="flex items-center gap-1 rounded-control px-2 py-1 text-sm text-text-secondary transition-colors duration-150 hover:bg-surface-2 hover:text-text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <X size={14} aria-hidden />
        {t("support.banner_exit")}
      </button>
    </div>
  );
}
