"use client";

/** The product's signature moment (03 §3): a prominent docked module for
 * the running study session. Large tabular-numeral clock in the display
 * face, quiet session metadata, one stop control. Purely presentational —
 * the dashboard owns all session state and actions. */

import { Square } from "lucide-react";

import { formatClock } from "@/lib/format";
import { useLang } from "@/lib/lang-context";
import { Button } from "./ui";

interface RunningSessionBarProps {
  taskTitle: string | null;
  courseLabel: string | null;
  elapsedSeconds: number;
  stopping: boolean;
  onStop: () => void;
}

export function RunningSessionBar({ taskTitle, courseLabel, elapsedSeconds, stopping, onStop }: RunningSessionBarProps) {
  const { t } = useLang();

  return (
    <section
      aria-label={t("tasks.session_running")}
      className="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-surface border border-accent/30 bg-accent/5 px-5 py-4"
    >
      <span aria-hidden className="relative flex h-2.5 w-2.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-pill bg-accent opacity-60 motion-reduce:animate-none" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-pill bg-accent" />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-text-muted">{t("tasks.session_running")}</p>
        <p className="truncate text-sm font-semibold text-text-primary">
          {taskTitle}
          {courseLabel && <span className="font-normal text-text-secondary"> · {courseLabel}</span>}
        </p>
      </div>
      <p
        dir="ltr"
        className="font-display ms-auto text-4xl font-semibold tabular-nums text-accent sm:text-5xl"
      >
        {formatClock(elapsedSeconds, "en")}
      </p>
      <Button variant="danger" size="sm" loading={stopping} onClick={onStop} className="ms-auto sm:ms-0">
        <Square size={14} aria-hidden />
        {t("tasks.stop_session")}
      </Button>
    </section>
  );
}
