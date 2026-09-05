"use client";

/** Branded 404 (Phase 6). Root-level not-found covers all segments; uses
 * the lang context for fa/en and mirrors direction via the root provider. */

import Link from "next/link";

import { Logomark } from "@/components/logomark";
import { Button } from "@/components/ui";
import { useLang } from "@/lib/lang-context";

export default function NotFound() {
  const { t } = useLang();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <span className="text-accent opacity-60">
        <Logomark size={40} />
      </span>
      <h1 className="text-2xl font-bold text-text-primary">{t("errors.not_found_title")}</h1>
      <p className="max-w-sm text-sm text-text-muted">{t("errors.not_found_description")}</p>
      <Link href="/app">
        <Button variant="secondary">{t("errors.back_home")}</Button>
      </Link>
    </main>
  );
}
