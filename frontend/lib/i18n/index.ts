/** Minimal i18n over the backend's canonical locale files (locales/*.json).
 * The JSON is copied verbatim from the Flask project — single source of
 * truth, no divergence. `t()` supports {placeholder} interpolation. */

import en from "../../locales/en.json";
import fa from "../../locales/fa.json";

// ^ locales/ is synced from the backend's canonical ../locales by
// scripts/sync-locales.mjs (predev/prebuild) — single source of truth.

export type Lang = "fa" | "en";

const dictionaries: Record<Lang, Record<string, unknown>> = { en, fa };

export const LANGS: Lang[] = ["fa", "en"];

function lookup(lang: Lang, key: string): string | undefined {
  const parts = key.split(".");
  let node: unknown = dictionaries[lang];
  for (const part of parts) {
    if (node && typeof node === "object" && part in (node as Record<string, unknown>)) {
      node = (node as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }
  return typeof node === "string" ? node : undefined;
}

export function t(lang: Lang, key: string, params?: Record<string, string | number>): string {
  const raw = lookup(lang, key) ?? lookup("en", key) ?? key;
  if (!params) return raw;
  return Object.entries(params).reduce(
    (acc, [name, value]) => acc.replaceAll(`{${name}}`, String(value)),
    raw,
  );
}

export function dirOf(lang: Lang): "rtl" | "ltr" {
  return lang === "fa" ? "rtl" : "ltr";
}

/** Resolve the UI language from an explicit preference, else the browser
 * language (Persian first), else fa (the product's default). */
export function resolveLang(preference: string | null | undefined): Lang {
  if (preference === "en" || preference === "fa") return preference;
  if (typeof navigator !== "undefined" && navigator.language?.toLowerCase().startsWith("fa")) {
    return "fa";
  }
  return "fa";
}
