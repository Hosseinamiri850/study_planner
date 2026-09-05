"use client";

/** Language segmented control (فا / EN) — replaces the bare <select> in
 * the header. Radios styled as segments keep native semantics. */

import { useLang } from "@/lib/lang-context";
import type { Lang } from "@/lib/i18n";

export function LangSwitch() {
  const { lang, setLang, t } = useLang();

  const segment = (value: Lang, label: string) => {
    const active = lang === value;
    return (
      <button
        type="button"
        key={value}
        onClick={() => setLang(value)}
        aria-pressed={active}
        className={`h-6 min-w-8 rounded-pill px-2 text-xs font-semibold transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent ${
          active
            ? "bg-accent text-accent-fg"
            : "text-text-muted hover:text-text-primary"
        }`}
      >
        {label}
      </button>
    );
  };

  return (
    <div
      role="group"
      aria-label={t("common.language")}
      className="flex items-center gap-0.5 rounded-pill border border-border-subtle bg-surface-2 p-0.5"
    >
      {segment("fa", "فا")}
      {segment("en", "EN")}
    </div>
  );
}
