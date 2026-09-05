"use client";

/** Course progress list extracted from the dashboard (audit C3): hides
 * zero-activity courses by default, sorts by activity, caps visible rows
 * with a show-all toggle. Purely presentational. */

import { useState } from "react";

import { formatHours } from "@/lib/format";
import { useLang } from "@/lib/lang-context";
import { Button } from "./ui";

export interface CourseProgress {
  key: string;
  name: string;
  total: number;
  done: number;
  hours: number;
}

interface CourseProgressListProps {
  courses: CourseProgress[];
  /** When true (fresh account), render the quiet hint instead of rows. */
  emptyHint?: string;
}

const DEFAULT_VISIBLE = 6;

export function CourseProgressList({ courses, emptyHint }: CourseProgressListProps) {
  const { t, lang } = useLang();
  const [showAll, setShowAll] = useState(false);

  // Only courses with tasks or logged hours carry signal — zero rows are
  // noise (audit C3).
  const active = courses
    .filter((course) => course.total > 0 || course.hours > 0)
    .sort((a, b) => b.hours - a.hours || b.done - a.done);

  if (active.length === 0) {
    if (!emptyHint) return null;
    return <p className="text-sm text-text-muted">{emptyHint}</p>;
  }

  const visible = showAll ? active : active.slice(0, DEFAULT_VISIBLE);

  return (
    <div className="space-y-3">
      <ul className="space-y-3">
        {visible.map((course) => {
          const pct = course.total > 0 ? Math.round((course.done / course.total) * 100) : 0;
          return (
            <li key={course.key}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="truncate text-sm font-medium text-text-primary">{course.name}</span>
                <span className="shrink-0 text-xs text-text-muted">
                  {course.done}/{course.total} · {formatHours(course.hours, lang)} {t("stats.hours_unit")}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-pill bg-surface-2">
                <div
                  className="h-full rounded-pill bg-accent transition-[width] duration-300"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
      {active.length > DEFAULT_VISIBLE && (
        <Button variant="ghost" size="sm" onClick={() => setShowAll((open) => !open)}>
          {showAll ? t("dashboard.show_fewer_courses") : `+ ${t("dashboard.show_all_courses")} (${active.length})`}
        </Button>
      )}
    </div>
  );
}
