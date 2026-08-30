"use client";

/** Dashboard stat cards + a lightweight bar chart for weekly hours. */

import { Card } from "./ui";
import { formatHours } from "@/lib/format";
import type { Lang } from "@/lib/i18n";

interface StatsCardsProps {
  todayHours: number;
  totalWeekHours: number;
  totalMonthHours: number;
  totalDone: number;
  totalTasks: number;
  lang: Lang;
  labels: {
    today: string;
    week: string;
    month: string;
    done: string;
    hoursUnit: string;
  };
}

export function StatsCards({ todayHours, totalWeekHours, totalMonthHours, totalDone, totalTasks, lang, labels }: StatsCardsProps) {
  const cards = [
    { label: labels.today, value: `${formatHours(todayHours, lang)} ${labels.hoursUnit}` },
    { label: labels.week, value: `${formatHours(totalWeekHours, lang)} ${labels.hoursUnit}` },
    { label: labels.month, value: `${formatHours(totalMonthHours, lang)} ${labels.hoursUnit}` },
    { label: labels.done, value: `${totalDone} / ${totalTasks}` },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label} className="p-4">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{card.label}</p>
          <p className="mt-1 text-2xl font-bold">{card.value}</p>
        </Card>
      ))}
    </div>
  );
}

/** Simple bar chart over `week_hours` (7 day map, ISO day keys). No chart
 * library — 7 bars render fine as divs and avoid a dependency. */
export function WeeklyChart({ weekHours, lang, label }: { weekHours: Record<string, number>; lang: Lang; label: string }) {
  const entries = Object.entries(weekHours).sort(([a], [b]) => a.localeCompare(b));
  const max = Math.max(...entries.map(([, value]) => value), 0.1);
  return (
    <section aria-label={label} className="space-y-2">
      <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">{label}</h2>
      <div className="flex h-32 items-end gap-2" dir="ltr">
        {entries.map(([day, hours]) => {
          const height = Math.max(4, Math.round((hours / max) * 100));
          const [, month, dayOfMonth] = day.split("-");
          return (
            <div key={day} className="flex flex-1 flex-col items-center gap-1">
              <div className="flex h-full w-full items-end rounded-t bg-indigo-200 dark:bg-indigo-800" title={`${day}: ${formatHours(hours, lang)}`}>
                <div className="w-full rounded-t bg-indigo-600 dark:bg-indigo-400" style={{ height: `${height}%` }} />
              </div>
              <span className="text-[10px] text-slate-500 dark:text-slate-400">{Number(dayOfMonth)}/{Number(month)}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
