"use client";

/** One task row: status, course badge, priority, estimated hours,
 * session start/stop, edit, delete. Sessions expand inline. */

import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatDuration } from "@/lib/format";
import { useLang } from "@/lib/lang-context";
import type { StudySession, Task } from "@/types/api";
import { Badge, Button, Spinner } from "./ui";

const priorityTone = { low: "default", medium: "warning", high: "danger" } as const;

interface TaskItemProps {
  task: Task;
  runningTaskId: number | null;
  runningSessionId: number | null;
  onToggle: (task: Task) => void;
  onDelete: (task: Task) => void;
  onEdit: (task: Task) => void;
  onStart: (task: Task) => Promise<void>;
  onStop: (task: Task, sessionId: number) => Promise<void>;
}

export function TaskItem({ task, runningTaskId, runningSessionId, onToggle, onDelete, onEdit, onStart, onStop }: TaskItemProps) {
  const { t, lang } = useLang();
  const { api } = useAuth();
  const [showSessions, setShowSessions] = useState(false);
  const [sessions, setSessions] = useState<StudySession[] | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const done = task.status === "completed";
  const running = runningTaskId === task.id && runningSessionId !== null;

  async function loadSessions() {
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      const data = await api.listSessions(task.id);
      setSessions(data.sessions);
    } catch {
      setSessionsError(t("errors.load_failed"));
    } finally {
      setSessionsLoading(false);
    }
  }

  useEffect(() => {
    if (showSessions && sessions === null && !sessionsLoading) void loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showSessions]);

  async function withBusy(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
      if (showSessions) await loadSessions();
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onToggle(task)}
          disabled={busy}
          aria-pressed={done}
          aria-label={done ? t("tasks.mark_pending") : t("tasks.mark_done")}
          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold transition-colors ${
            done
              ? "border-emerald-600 bg-emerald-600 text-white"
              : "border-slate-300 text-transparent hover:border-emerald-500 dark:border-slate-600"
          }`}
        >
          ✓
        </button>
        <div className="min-w-0 flex-1">
          <p className={`truncate text-sm font-medium ${done ? "text-slate-400 line-through dark:text-slate-500" : ""}`}>
            {task.title}
          </p>
          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Badge tone={priorityTone[task.priority]}>{t(`tasks.priority_${task.priority}`)}</Badge>
            <span className="truncate">{task.course_key}</span>
            <span>· {task.estimated_hours}h</span>
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {running && (
            <Badge tone="success">
              <span className="me-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" aria-hidden />
              {t("tasks.session_running")}
            </Badge>
          )}
          {!done && !running && (
            <Button
              variant="secondary"
              className="px-2 py-1 text-xs"
              disabled={busy}
              onClick={() => void withBusy(() => onStart(task))}
            >
              {t("tasks.start_session")}
            </Button>
          )}
          {running && (
            <Button
              variant="primary"
              className="px-2 py-1 text-xs"
              disabled={busy}
              onClick={() => runningSessionId !== null && void withBusy(() => onStop(task, runningSessionId))}
            >
              {t("tasks.stop_session")}
            </Button>
          )}
          <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => setShowSessions((open) => !open)} aria-expanded={showSessions}>
            {t("tasks.sessions")}
          </Button>
          <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => onEdit(task)}>
            {t("common.edit")}
          </Button>
          <Button variant="ghost" className="px-2 py-1 text-xs text-red-600 dark:text-red-400" onClick={() => onDelete(task)}>
            {t("common.delete")}
          </Button>
        </div>
      </div>
      {showSessions && (
        <div className="mt-3 border-t border-slate-100 pt-3 dark:border-slate-700">
          {sessionsLoading && <Spinner label={t("common.loading")} />}
          {sessionsError && <p className="text-sm text-red-600 dark:text-red-400">{sessionsError}</p>}
          {sessions !== null && !sessionsLoading && sessions.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">{t("tasks.no_sessions")}</p>
          )}
          {sessions !== null && sessions.length > 0 && (
            <ul className="space-y-1 text-xs">
              {sessions.map((session) => (
                <li key={session.id} className="flex flex-wrap items-center gap-2 text-slate-600 dark:text-slate-300">
                  <span>{formatDateTime(session.started_at, lang)}</span>
                  <span aria-hidden>→</span>
                  <span>{session.is_open ? t("tasks.session_running") : formatDateTime(session.ended_at, lang)}</span>
                  <Badge tone={session.is_open ? "success" : "default"}>{formatDuration(session.duration, lang)}</Badge>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  );
}
