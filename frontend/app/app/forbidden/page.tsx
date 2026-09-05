"use client";

/** Branded 403 for role-gated deep links (audit F3). The API enforces
 * authorization; this page is the SPA's UX response when a caller lands
 * somewhere their role doesn't permit. */

import Link from "next/link";
import { ShieldX } from "lucide-react";

import { Button } from "@/components/ui";
import { useLang } from "@/lib/lang-context";

export default function ForbiddenPage() {
  const { t } = useLang();

  return (
    <main className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
      <ShieldX size={40} aria-hidden className="text-danger" />
      <h1 className="text-2xl font-bold text-text-primary">{t("errors.forbidden_title")}</h1>
      <p className="max-w-sm text-sm text-text-muted">{t("errors.forbidden_description")}</p>
      <Link href="/app">
        <Button variant="secondary">{t("errors.back_home")}</Button>
      </Link>
    </main>
  );
}
