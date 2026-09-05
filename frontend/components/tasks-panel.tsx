"use client";

/** One task row (Phase 4 anatomy): completion check, title, meta line,
 * priority edge mark (audit B3 — weight + rail, not pill-spam), session
 * start/stop, icon actions. Sessions expand inline. */

import { useEffect, useState } from "react";
import { Check, Pencil, Play, Square, Timer, Trash2 } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatDuration } from "@/lib/format";
import { useLang } from "@/lib/lang-context";
import type { StudySession, Task } from "@/types/api";
import { Badge, Button, Spinner } from "./ui";

const priorityRail: Record<Task["priority"], string> = {
  low: "bg-transparent",
  medium: "bg-warning",
  high: "bg-danger",
};

const priorityWeight: Record<Task["priority"], string> = {
  low: "font-normal",
  medium: "font-medium",
  high: "font-semibold",
};

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

  const iconAction =
    "flex h-8 w-8 items-center justify-center rounded-control text-text-secondary transition-colors duration-150 hover:bg-surface-2 hover:text-text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <li
      className={`group relative rounded-surface border border-border-subtle bg-surface-1 ps-4 pe-3 py-3 transition-colors duration-150 ${
        running ? "border-accent/40 bg-accent/5" : ""
      }`}
    >
      {/* priority edge mark */}
      <span
        aria-hidden
        className={`absolute inset-y-3 start-0 w-1 rounded-pill ${priorityRail[task.priority]}`}
      />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <button
          type="button"
          onClick={() => onToggle(task)}
          disabled={busy}
          aria-pressed={done}
          aria-label={done ? t("tasks.mark_pending") : t("tasks.mark_done")}
          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-pill border-2 transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
            done
              ? "border-success bg-success text-white"
              : "border-border-strong text-transparent hover:border-success"
          }`}
        >
          <Check size={14} strokeWidth={3} aria-hidden />
        </button>
        <div className="min-w-0 flex-1">
          <p className={`truncate text-sm ${priorityWeight[task.priority]} ${done ? "text-text-muted line-through" : "text-text-primary"}`}>
            {task.title}
          </p>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-text-muted">
            <span className="truncate" dir="auto">{task.course_key}</span>
            <span aria-hidden>·</span>
            <span className="tabular-nums">{task.estimated_hours}h</span>
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {running && (
            <Badge tone="success">
              <span className="me-1 inline-block h-1.5 w-1.5 animate-pulse rounded-pill bg-success motion-reduce:animate-none" aria-hidden />
              {t("tasks.session_running")}
            </Badge>
          )}
          {!done && !running && (
            <Button
              variant="secondary"
              size="sm"
              disabled={busy}
              onClick={() => void withBusy(() => onStart(task))}
              aria-label={t("tasks.start_session")}
            >
              <Play size={14} aria-hidden />
              <span className="hidden sm:inline">{t("tasks.start_session")}</span>
            </Button>
          )}
          {running && (
            <Button
              variant="primary"
              size="sm"
              disabled={busy}
              onClick={() => runningSessionId !== null && void withBusy(() => onStop(task, runningSessionId))}
              aria-label={t("tasks.stop_session")}
            >
              <Square size={14} aria-hidden />
              <span className="hidden sm:inline">{t("tasks.stop_session")}</span>
            </Button>
          )}
          <button
            type="button"
            onClick={() => setShowSessions((open) => !open)}
            aria-expanded={showSessions}
            aria-label={t("tasks.sessions")}
            disabled={busy}
            className={iconAction}
          >
            <Timer size={16} aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => onEdit(task)}
            aria-label={t("common.edit")}
            disabled={busy}
            className={iconAction}
          >
            <Pencil size={16} aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => onDelete(task)}
            aria-label={t("common.delete")}
            disabled={busy}
            className={`${iconAction} hover:text-danger`}
          >
            <Trash2 size={16} aria-hidden />
          </button>
        </div>
      </div>
      {showSessions && (
        <div className="mt-3 border-t border-border-subtle pt-3">
          {sessionsLoading && <Spinner label={t("common.loading")} />}
          {sessionsError && <p className="text-sm text-danger">{sessionsError}</p>}
          {sessions !== null && !sessionsLoading && sessions.length === 0 && (
            <p className="text-sm text-text-muted">{t("tasks.no_sessions")}</p>
          )}
          {sessions !== null && sessions.length > 0 && (
            <ul className="space-y-1 text-xs">
              {sessions.map((session) => (
                <li key={session.id} className="flex flex-wrap items-center gap-2 text-text-secondary">
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
