"use client";

/** Create/edit task dialog on Radix Dialog: focus trap, scroll lock, Esc,
 * backdrop cancel — all by construction. Course selector fed from
 * /api/courses; priority + estimated hours validated client-side (backend
 * re-validates). Form logic unchanged from the pre-Radix version. */

import { useEffect, useState, type FormEvent } from "react";
import * as Dialog from "@radix-ui/react-dialog";

import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import { validEstimatedHours } from "@/lib/validation";
import type { Course, Task } from "@/types/api";
import { Alert, Button, Field, Input, Select, Textarea } from "./ui";

interface TaskFormDialogProps {
  open: boolean;
  /** Present = edit mode. */
  task?: Task | null;
  courses: Course[];
  onSaved: (task: Task) => void;
  onCancel: () => void;
}

export function TaskFormDialog({ open, task, courses, onSaved, onCancel }: TaskFormDialogProps) {
  const { t, lang } = useLang();
  const { api } = useAuth();

  const [courseKey, setCourseKey] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high">("medium");
  const [hours, setHours] = useState("1");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const editing = task != null;

  useEffect(() => {
    if (!open) return;
    setCourseKey(task?.course_key ?? courses[0]?.key ?? "");
    setTitle(task?.title ?? "");
    setDescription(task?.description ?? "");
    setPriority(task?.priority ?? "medium");
    setHours(String(task?.estimated_hours ?? 1));
    setFieldErrors({});
    setServerError(null);
  }, [open, task, courses]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setServerError(null);
    const nextErrors: Record<string, string> = {};
    if (!courseKey) nextErrors.courseKey = t("tasks.empty_courses");
    const parsedHours = Number(hours);
    if (!Number.isFinite(parsedHours) || !validEstimatedHours(parsedHours)) nextErrors.hours = t("validation.hours");
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      if (editing && task) {
        const { task: saved } = await api.updateTask(task.id, {
          course_key: courseKey,
          title: title.trim(),
          description,
          priority,
          estimated_hours: parsedHours,
        });
        onSaved(saved);
      } else {
        const { task: saved } = await api.createTask({
          course_key: courseKey,
          title: title.trim() || undefined,
          description,
          priority,
          estimated_hours: parsedHours,
        });
        onSaved(saved);
      }
    } catch (err) {
      setServerError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(next: boolean) => { if (!next) onCancel(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-900/50 data-[state=open]:animate-in data-[state=closed]:animate-out" />
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <Dialog.Content
            className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-surface border border-border-subtle bg-surface-1 p-5 shadow-lg data-[state=open]:animate-in data-[state=closed]:animate-out"
          >
            <Dialog.Title className="mb-4 text-base font-semibold text-text-primary">
              {editing ? t("tasks.edit_title") : t("tasks.new_task")}
            </Dialog.Title>
            <form onSubmit={onSubmit} className="space-y-4" noValidate>
              {serverError && <Alert tone="error">{serverError}</Alert>}
              <Field label={t("tasks.course")} htmlFor="tf-course" error={fieldErrors.courseKey}>
                <Select id="tf-course" value={courseKey} onChange={(event) => setCourseKey(event.target.value)}>
                  {courses.map((course) => (
                    <option key={course.key} value={course.key}>
                      {lang === "fa" ? course.name_fa : course.name_en}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t("tasks.task_title")} htmlFor="tf-title">
                <Input id="tf-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={255} />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("tasks.priority")} htmlFor="tf-priority" error={fieldErrors.priority}>
                  <Select id="tf-priority" value={priority} onChange={(event) => setPriority(event.target.value as "low" | "medium" | "high")}>
                    <option value="low">{t("tasks.priority_low")}</option>
                    <option value="medium">{t("tasks.priority_medium")}</option>
                    <option value="high">{t("tasks.priority_high")}</option>
                  </Select>
                </Field>
                <Field label={t("tasks.estimated_hours")} htmlFor="tf-hours" error={fieldErrors.hours}>
                  <Input
                    id="tf-hours"
                    type="number"
                    inputMode="decimal"
                    min={0}
                    max={24}
                    step={0.5}
                    value={hours}
                    onChange={(event) => setHours(event.target.value)}
                  />
                </Field>
              </div>
              <Field label={t("tasks.description")} htmlFor="tf-description">
                <Textarea id="tf-description" rows={3} value={description} onChange={(event) => setDescription(event.target.value)} />
              </Field>
              <div className="flex justify-end gap-2">
                <Dialog.Close asChild>
                  <Button type="button" variant="secondary" disabled={submitting}>
                    {t("common.cancel")}
                  </Button>
                </Dialog.Close>
                <Button type="submit" loading={submitting}>
                  {editing ? t("common.save") : t("common.create")}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </div>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
