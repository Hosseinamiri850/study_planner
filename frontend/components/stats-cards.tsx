"use client";

/** Dashboard context-column data displays (Phase 4): a compact stat strip
 * (label-quiet / value-loud, no boxes — audit C2) and a token-styled
 * recharts bar chart with localized weekday axis (audit D5, G2). */

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatHours } from "@/lib/format";
import type { Lang } from "@/lib/i18n";
import { useLang } from "@/lib/lang-context";

interface StatsStripProps {
  todayHours: number;
  totalWeekHours: number;
  totalMonthHours: number;
  totalDone: number;
  totalTasks: number;
}

export function StatsStrip({ todayHours, totalWeekHours, totalMonthHours, totalDone, totalTasks }: StatsStripProps) {
  const { t, lang } = useLang();
  const unit = t("stats.hours_unit");

  const items = [
    { label: t("stats.today_hours"), value: `${formatHours(todayHours, lang)} ${unit}` },
    { label: t("stats.this_week_total"), value: `${formatHours(totalWeekHours, lang)} ${unit}` },
    { label: t("stats.total_month_hours"), value: `${formatHours(totalMonthHours, lang)} ${unit}` },
    { label: t("stats.done_tasks"), value: `${totalDone.toLocaleString(lang === "fa" ? "fa-IR" : "en-US")} / ${totalTasks.toLocaleString(lang === "fa" ? "fa-IR" : "en-US")}` },
  ];

  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-5">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="tracking-label text-[11px] font-medium text-text-muted">{item.label}</dt>
          <dd className="font-display mt-1 truncate text-2xl font-semibold tabular-nums text-text-primary" dir="auto">
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** ISO day-key map (yyyy-mm-dd) -> localized bar chart. Weekday initials
 * per locale replace raw day/month fragments (audit G2). */
const WEEKDAY_KEYS: Record<Lang, string[]> = {
  en: ["S", "M", "T", "W", "T", "F", "S"],
  fa: ["ی", "د", "س", "چ", "پ", "ج", "ش"], // یک‌شنبه .. شنبه (Sun-first, matches getDay())
};

export function WeeklyChart({ weekHours, label }: { weekHours: Record<string, number>; label: string }) {
  const { lang } = useLang();
  const weekdays = WEEKDAY_KEYS[lang];

  const data = Object.entries(weekHours)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, hours]) => {
      const date = new Date(`${day}T00:00:00`);
      const weekday = weekdays[date.getDay()] ?? "";
      return { day, weekday, hours };
    });

  return (
    <section aria-label={label} className="space-y-3">
      <h2 className="text-sm font-semibold text-text-primary">{label}</h2>
      <div className="h-36" dir="ltr">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="weekday"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
              interval={0}
            />
            <YAxis hide domain={[0, "dataMax"]} />
            <Tooltip
              cursor={{ fill: "var(--color-surface-2)" }}
              contentStyle={{
                background: "var(--color-surface-1)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "var(--radius-control)",
                fontSize: 12,
                color: "var(--color-text-primary)",
              }}
              formatter={(value) => [
                `${formatHours(Number(value ?? 0), lang)} ${label.split(" ")[0] ?? ""}`,
                "",
              ]}
              labelFormatter={(day) => String(day)}
            />
            <Bar dataKey="hours" radius={[3, 3, 0, 0]} maxBarSize={28}>
              {data.map((entry) => (
                <Cell
                  key={entry.day}
                  fill={entry.hours > 0 ? "var(--color-accent)" : "var(--color-border-subtle)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
