"use client";

/** Student dashboard, Phase 4: asymmetric two-zone layout (03 §3). Start
 * zone = running session + task list (workspace); end zone = stat strip,
 * weekly chart, course progress (context). All session/timer logic is
 * carried verbatim from the pre-redesign page — only presentation moved.
 * Live timer ticks locally for the open session; the backend remains the
 * source of truth for totals. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { CourseProgressList } from "@/components/course-progress-list";
import { RunningSessionBar } from "@/components/running-session-bar";
import { StatsStrip, WeeklyChart } from "@/components/stats-cards";
import { TaskFormDialog } from "@/components/task-form-dialog";
import { TaskItem } from "@/components/tasks-panel";
import { Alert, Button, Card, EmptyState, Skeleton } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import type { Course, DashboardStats, Task, TaskListPaginatedResponse } from "@/types/api";

const PER_PAGE = 20;

export default function DashboardPage() {
  const { user, api } = useAuth();
  const { t, lang } = useLang();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [tasksError, setTasksError] = useState<string | null>(null);
  const [runningTaskId, setRunningTaskId] = useState<number | null>(null);
  const [runningSessionId, setRunningSessionId] = useState<number | null>(null);
  const [runningSince, setRunningSince] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);

  const [formOpen, setFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deletingTask, setDeletingTask] = useState<Task | null>(null);
  const [deleting, setDeleting] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadStats = useCallback(async () => {
    setStatsError(null);
    try {
      setStats(await api.dashboardStats());
    } catch (err) {
      setStatsError(errorMessage(err));
    }
  }, [api]);

  const loadTasks = useCallback(
    async (targetPage: number, opts?: { restoreRunning?: boolean }) => {
      setTasksError(null);
      try {
        const data = (await api.listTasks(targetPage, PER_PAGE)) as TaskListPaginatedResponse;
        setTasks(data.tasks);
        setPages(Math.max(data.pages, 1));
        setTotal(data.total);
        setPage(data.page);
        // Re-sync the running-session indicator with the server: find the
        // open session among the page's tasks (server is authoritative).
        const open = data.tasks.find((task) => task.open_session_id != null);
        if (open) {
          setRunningTaskId(open.id);
          setRunningSessionId(open.open_session_id);
          if (opts?.restoreRunning && runningSince === null) {
            // Page reload mid-session: re-anchor the display timer from the
            // user's local clock offset against the session's start. The
            // backend stores naive UTC; compute elapsed from the session
            // row itself so the timer survives reloads.
            try {
              const { sessions } = await api.listSessions(open.id);
              const session = sessions.find((s) => s.id === open.open_session_id);
              if (session?.started_at) {
                const startedUtcMs = Date.parse(session.started_at.endsWith("Z") ? session.started_at : `${session.started_at}Z`);
                if (!Number.isNaN(startedUtcMs)) setRunningSince(startedUtcMs);
                else setRunningSince(Date.now());
              } else {
                setRunningSince(Date.now());
              }
            } catch {
              setRunningSince(Date.now());
            }
            setElapsed(0);
          }
        } else {
          setRunningTaskId(null);
          setRunningSessionId(null);
          setRunningSince(null);
        }
      } catch (err) {
        setTasksError(errorMessage(err));
      }
    },
    // runningTaskId/runningSince intentionally omitted: only used to
    // decide whether to restore, not to refetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [api],
  );

  useEffect(() => {
    void loadStats();
    void loadTasks(1, { restoreRunning: true });
    api
      .listCourses()
      .then((data) => setCourses(data.courses))
      .catch(() => setCourses([]));
  }, [api, loadStats, loadTasks]);

  // Local ticking timer for the open session (display only).
  useEffect(() => {
    if (runningTaskId === null || runningSince === null) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - runningSince) / 1000)), 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [runningTaskId, runningSince]);

  async function startSession(task: Task) {
    setActionError(null);
    try {
      const { session } = await api.startSession(task.id);
      setRunningTaskId(task.id);
      setRunningSessionId(session.id);
      // Backend timestamps are naive UTC; Date() would parse them as local
      // time and skew the timer by the zone offset. Prefer local now().
      setRunningSince(Date.now());
      setElapsed(0);
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  async function stopSession(task: Task, sessionId: number) {
    setStopping(true);
    setActionError(null);
    try {
      await api.stopSession(task.id, sessionId);
      setRunningTaskId(null);
      setRunningSessionId(null);
      setRunningSince(null);
      void loadStats();
      void loadTasks(page);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setStopping(false);
    }
  }

  async function toggleTask(task: Task) {
    setActionError(null);
    try {
      await api.updateTask(task.id, { status: task.status === "completed" ? "pending" : "completed" });
      void loadStats();
      void loadTasks(page);
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  async function confirmDelete() {
    if (!deletingTask) return;
    setDeleting(true);
    try {
      await api.deleteTask(deletingTask.id);
      setDeletingTask(null);
      void loadStats();
      void loadTasks(page);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setDeleting(false);
    }
  }

  const onTaskSaved = useMemo(
    () => (saved: Task) => {
      setFormOpen(false);
      setEditingTask(null);
      setTasks((current) =>
        current == null ? [saved] : current.some((task) => task.id === saved.id) ? current.map((task) => (task.id === saved.id ? saved : task)) : [saved, ...current],
      );
      void loadStats();
    },
    [loadStats],
  );

  const runningTask = tasks?.find((task) => task.id === runningTaskId) ?? null;
  const isNewUser = stats !== null && stats.total_tasks === 0;

  const openTaskForm = (task: Task | null) => {
    setEditingTask(task);
    setFormOpen(true);
  };

  const suggestedCourse = courses?.[0] ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="tracking-label text-[11px] font-medium text-text-muted">
            {lang === "fa" ? "داشبورد" : "Dashboard"}
          </p>
          <h1 className="mt-0.5 text-xl font-bold text-text-primary">
            {t("dashboard.greeting", { name: user?.fullname ?? user?.username ?? "" })}
          </h1>
        </div>
        <Button onClick={() => openTaskForm(null)}>
          + {t("tasks.new_task")}
        </Button>
      </div>

      {actionError && <Alert tone="error">{actionError}</Alert>}

      {statsError && (
        <Alert tone="error">
          {statsError}{" "}
          <Button variant="secondary" size="sm" className="ms-2" onClick={() => void loadStats()}>
            {t("common.retry")}
          </Button>
        </Alert>
      )}

      {/* Running session — the hero zone (start/workspace top) */}
      {runningTaskId !== null && runningSince !== null && (
        <RunningSessionBar
          taskTitle={runningTask?.title ?? null}
          courseLabel={runningTask?.course_key ?? null}
          elapsedSeconds={elapsed}
          stopping={stopping}
          onStop={() => {
            if (runningTask && runningSessionId !== null) void stopSession(runningTask, runningSessionId);
          }}
        />
      )}

      {/* Asymmetric two-zone grid (03 §3): workspace / context. */}
      <div className="grid gap-8 lg:grid-cols-12">
        {/* Workspace zone */}
        <div className="space-y-4 lg:col-span-8">
          <section aria-label={t("tasks.title")} className="space-y-3">
            <div className="flex items-baseline justify-between">
              <h2 className="text-lg font-semibold text-text-primary">{t("tasks.title")}</h2>
              {tasks && (
                <span className="text-sm tabular-nums text-text-muted">
                  {total.toLocaleString(lang === "fa" ? "fa-IR" : "en-US")}
                </span>
              )}
            </div>
            {tasksError && (
              <Alert tone="error">
                {tasksError}{" "}
                <Button variant="secondary" size="sm" className="ms-2" onClick={() => void loadTasks(page)}>
                  {t("common.retry")}
                </Button>
              </Alert>
            )}
            {!tasks && !tasksError && (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Card key={index} className="p-3">
                    <Skeleton className="h-4 w-2/3" />
                    <Skeleton className="mt-2 h-3 w-1/3" />
                  </Card>
                ))}
              </div>
            )}
            {tasks && tasks.length === 0 && (
              <EmptyState
                title={t("tasks.empty_title")}
                description={
                  suggestedCourse
                    ? `${t("tasks.empty_description")} ${t("tasks.suggested_course")}: ${lang === "fa" ? suggestedCourse.name_fa : suggestedCourse.name_en}`
                    : t("tasks.empty_description")
                }
                action={
                  <Button onClick={() => openTaskForm(null)}>
                    + {t("tasks.new_task")}
                  </Button>
                }
              />
            )}
            {tasks && tasks.length > 0 && (
              <ul className="space-y-2">
                {tasks.map((task) => (
                  <TaskItem
                    key={task.id}
                    task={task}
                    runningTaskId={runningTaskId}
                    runningSessionId={runningSessionId}
                    onToggle={(target) => void toggleTask(target)}
                    onDelete={(target) => setDeletingTask(target)}
                    onEdit={openTaskForm}
                    onStart={startSession}
                    onStop={stopSession}
                  />
                ))}
              </ul>
            )}
            {tasks && pages > 1 && (
              <nav className="flex items-center justify-center gap-3" aria-label={t("a11y.pagination")}>
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => void loadTasks(page - 1)}>
                  {t("tasks.prev_page")}
                </Button>
                <span className="text-xs text-text-muted">{t("tasks.page_of", { page, pages })}</span>
                <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => void loadTasks(page + 1)}>
                  {t("tasks.next_page")}
                </Button>
              </nav>
            )}
          </section>
        </div>

        {/* Context zone */}
        <div className="space-y-8 lg:col-span-4">
          {!stats && !statsError && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          )}
          {stats && (
            <>
              <StatsStrip
                todayHours={stats.today_hours}
                totalWeekHours={stats.total_week_hours}
                totalMonthHours={stats.total_month_hours}
                totalDone={stats.total_done}
                totalTasks={stats.total_tasks}
              />
              <div className="border-t border-border-subtle pt-6">
                <WeeklyChart weekHours={stats.week_hours} label={t("stats.weekly")} />
              </div>
              <div className="border-t border-border-subtle pt-6">
                <h2 className="mb-3 text-sm font-semibold text-text-primary">{t("stats.course_stats")}</h2>
                {isNewUser ? (
                  <p className="text-sm text-text-muted">{t("dashboard.empty_courses_hint")}</p>
                ) : (
                  <CourseProgressList
                    courses={Object.entries(stats.courses).map(([key, course]) => ({
                      key,
                      name: course.name,
                      total: course.total,
                      done: course.done,
                      hours: course.hours,
                    }))}
                  />
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {formOpen && courses && (
        <TaskFormDialog
          open={formOpen}
          task={editingTask}
          courses={courses}
          onSaved={onTaskSaved}
          onCancel={() => {
            setFormOpen(false);
            setEditingTask(null);
          }}
        />
      )}

      <ConfirmDialog
        open={deletingTask !== null}
        title={t("tasks.delete_confirm_title")}
        description={t("tasks.delete_confirm_body")}
        confirmLabel={t("common.delete")}
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeletingTask(null)}
      />
    </div>
  );
}
