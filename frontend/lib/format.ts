/** Display formatting helpers. Locale-aware (fa/en) with Gregorian dates
 * — the backend uses ISO dates and the Jinja app shows Persian labels over
 * Gregorian dates; matching that keeps the two UIs consistent. */

import type { Lang } from "./i18n";

export function formatHours(hours: number, lang: Lang): string {
  const formatted = hours.toLocaleString(lang === "fa" ? "fa-IR" : "en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return formatted;
}

/** Seconds -> "H:MM:SS" live-timer label (tabular numerals assumed). */
export function formatClock(totalSeconds: number, lang: Lang): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const seconds = safe % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  const asGroup = (n: number) => n.toLocaleString(lang === "fa" ? "fa-IR" : "en-US");
  return `${asGroup(hours)}:${pad(minutes).replace(/\d/g, (d) => asGroup(Number(d)))}:${pad(seconds).replace(/\d/g, (d) => asGroup(Number(d)))}`;
}

/** Seconds -> "1h 30m" style label (session durations). */
export function formatDuration(seconds: number | null | undefined, lang: Lang): string {
  if (seconds == null) return "—";
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const h = hours.toLocaleString(lang === "fa" ? "fa-IR" : "en-US");
  const m = minutes.toLocaleString(lang === "fa" ? "fa-IR" : "en-US");
  if (hours === 0) return `${m}m`;
  if (minutes === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/** ISO timestamp -> localized short date-time. */
export function formatDateTime(iso: string | null | undefined, lang: Lang): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(lang === "fa" ? "fa-IR" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Local (browser) date in ISO yyyy-mm-dd, matching how the backend keys
 * its day buckets (naive server-local dates). */
export function isoDay(date: Date): string {
  const year = String(date.getFullYear()).padStart(4, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
