"use client";

/** Admin (Phase 5): majors + courses CRUD with a distinct elevated-zone
 * marker. Courses grouped by major; action feedback via toast; the
 * protected-major rule surfaced as a note, not just a disabled button.
 * Gated on is_admin (UI gating only — the API enforces authorization and
 * returns 403 for non-admins, which this page surfaces as an error alert
 * rather than crashing). */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { Alert, Badge, Button, Card, Field, Input, Select, Skeleton } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import type { Major } from "@/types/api";

interface PendingDelete {
  type: "major" | "course";
  id: number;
  name: string;
}

const PROTECTED_MAJOR_KEY = "computer_science";

export default function AdminPage() {
  const { user, api } = useAuth();
  const { t, lang } = useLang();
  const { showToast } = useToast();
  const router = useRouter();

  const [majors, setMajors] = useState<Major[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // new major form
  const [majorNameFa, setMajorNameFa] = useState("");
  const [majorNameEn, setMajorNameEn] = useState("");
  const [majorKey, setMajorKey] = useState("");
  const [creatingMajor, setCreatingMajor] = useState(false);

  // new course form
  const [courseMajorId, setCourseMajorId] = useState("");
  const [courseNameFa, setCourseNameFa] = useState("");
  const [courseNameEn, setCourseNameEn] = useState("");
  const [courseKey, setCourseKey] = useState("");
  const [creatingCourse, setCreatingCourse] = useState(false);

  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null);
  const [deleting, setDeleting] = useState(false);

  const isAdmin = user?.is_admin === true;

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await api.listMajors();
      setMajors(data.majors);
      setCourseMajorId((current) => current || (data.majors[0] ? String(data.majors[0].id) : ""));
    } catch (err) {
      setLoadError(errorMessage(err));
      setMajors([]);
    }
  }, [api]);

  useEffect(() => {
    if (isAdmin) void load();
  }, [isAdmin, load]);

  useEffect(() => {
    // Signed-in non-admins: bounce quietly (middleware lets the cookie
    // through; the role check happens here and at the API).
    if (user && !isAdmin) router.replace("/app");
  }, [user, isAdmin, router]);

  if (!user) return null;

  async function createMajor(event: React.FormEvent) {
    event.preventDefault();
    setActionError(null);
    if (!majorNameFa.trim() || !majorNameEn.trim()) {
      setActionError(t("auth.fill_all_fields"));
      return;
    }
    setCreatingMajor(true);
    try {
      await api.createMajor({
        name_fa: majorNameFa.trim(),
        name_en: majorNameEn.trim(),
        key: majorKey.trim() || undefined,
      });
      setMajorNameFa("");
      setMajorNameEn("");
      setMajorKey("");
      showToast("success", t("profile.save_success"));
      await load();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setCreatingMajor(false);
    }
  }

  async function createCourse(event: React.FormEvent) {
    event.preventDefault();
    setActionError(null);
    const majorId = Number(courseMajorId);
    if (!courseNameFa.trim() || !courseNameEn.trim() || !Number.isInteger(majorId) || majorId <= 0) {
      setActionError(t("auth.fill_all_fields"));
      return;
    }
    setCreatingCourse(true);
    try {
      await api.createCourse({
        name_fa: courseNameFa.trim(),
        name_en: courseNameEn.trim(),
        major_id: majorId,
        key: courseKey.trim() || undefined,
      });
      setCourseNameFa("");
      setCourseNameEn("");
      setCourseKey("");
      showToast("success", t("profile.save_success"));
      await load();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setCreatingCourse(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    setActionError(null);
    try {
      if (pendingDelete.type === "major") {
        await api.deleteMajor(pendingDelete.id);
      } else {
        await api.deleteCourse(pendingDelete.id);
      }
      setPendingDelete(null);
      showToast("success", t("profile.save_success"));
      await load();
    } catch (err) {
      setActionError(errorMessage(err));
      setPendingDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  if (!isAdmin) return null;

  return (
    <div className="space-y-6">
      <div>
        <p className="flex items-center gap-1.5 text-[11px] font-medium text-text-muted">
          <ShieldCheck size={12} aria-hidden className="text-accent" />
          {lang === "fa" ? "منطقه مدیریت" : "Admin zone"}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-text-primary">{t("admin.title")}</h1>
      </div>

      {loadError && (
        <Alert tone="error">
          {loadError}{" "}
          <Button variant="secondary" size="sm" className="ms-2" onClick={() => void load()}>
            {t("common.retry")}
          </Button>
        </Alert>
      )}
      {actionError && <Alert tone="error">{actionError}</Alert>}

      {!majors && !loadError && (
        <Card className="space-y-2 p-5">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-8 w-full" />
          ))}
        </Card>
      )}

      {majors && (
        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("admin.majors")}</h2>
            <form onSubmit={createMajor} className="space-y-3 border-b border-border-subtle pb-5">
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("admin.name_fa")} htmlFor="major-name-fa">
                  <Input id="major-name-fa" value={majorNameFa} onChange={(event) => setMajorNameFa(event.target.value)} dir="rtl" />
                </Field>
                <Field label={t("admin.name_en")} htmlFor="major-name-en">
                  <Input id="major-name-en" value={majorNameEn} onChange={(event) => setMajorNameEn(event.target.value)} dir="ltr" />
                </Field>
              </div>
              <Field label={t("admin.key_optional")} htmlFor="major-key">
                <Input id="major-key" value={majorKey} onChange={(event) => setMajorKey(event.target.value)} dir="ltr" />
              </Field>
              <Button type="submit" loading={creatingMajor}>
                + {t("common.create")}
              </Button>
            </form>
            <ul className="mt-4 space-y-2">
              {majors.map((major) => (
                <li key={major.id} className="flex items-center justify-between rounded-control border border-border-subtle px-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-text-primary">{lang === "fa" ? major.name_fa : major.name_en}</p>
                    <p className="text-xs text-text-muted" dir="ltr">
                      {major.key} · {major.courses.length}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-danger"
                    disabled={major.key === PROTECTED_MAJOR_KEY}
                    title={major.key === PROTECTED_MAJOR_KEY ? t("admin.protected_major") : undefined}
                    onClick={() => setPendingDelete({ type: "major", id: major.id, name: lang === "fa" ? major.name_fa : major.name_en })}
                  >
                    {t("common.delete")}
                  </Button>
                </li>
              ))}
            </ul>
            {majors.some((major) => major.key === PROTECTED_MAJOR_KEY) && (
              <p className="mt-3 text-xs text-text-muted">{t("admin.protected_major")}</p>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("admin.courses")}</h2>
            <form onSubmit={createCourse} className="space-y-3 border-b border-border-subtle pb-5">
              <Field label={t("admin.major")} htmlFor="course-major">
                <Select id="course-major" value={courseMajorId} onChange={(event) => setCourseMajorId(event.target.value)}>
                  {majors.map((major) => (
                    <option key={major.id} value={major.id}>
                      {lang === "fa" ? major.name_fa : major.name_en}
                    </option>
                  ))}
                </Select>
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("admin.name_fa")} htmlFor="course-name-fa">
                  <Input id="course-name-fa" value={courseNameFa} onChange={(event) => setCourseNameFa(event.target.value)} dir="rtl" />
                </Field>
                <Field label={t("admin.name_en")} htmlFor="course-name-en">
                  <Input id="course-name-en" value={courseNameEn} onChange={(event) => setCourseNameEn(event.target.value)} dir="ltr" />
                </Field>
              </div>
              <Field label={t("admin.key_optional")} htmlFor="course-key">
                <Input id="course-key" value={courseKey} onChange={(event) => setCourseKey(event.target.value)} dir="ltr" />
              </Field>
              <Button type="submit" loading={creatingCourse}>
                + {t("common.create")}
              </Button>
            </form>
            <div className="mt-4 space-y-4">
              {majors.map((major) => (
                <div key={major.id}>
                  <p className="mb-1.5 text-xs font-semibold text-text-secondary">{lang === "fa" ? major.name_fa : major.name_en}</p>
                  {major.courses.length === 0 ? (
                    <p className="text-xs text-text-muted">{t("tasks.empty_courses")}</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {major.courses.map((course) => (
                        <li key={course.id} className="flex items-center justify-between rounded-control border border-border-subtle px-3 py-1.5">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-text-primary">{lang === "fa" ? course.name_fa : course.name_en}</p>
                            <p className="text-xs text-text-muted" dir="ltr">
                              <Badge>{major.key}</Badge> {course.key}
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-danger"
                            onClick={() => setPendingDelete({ type: "course", id: course.id, name: lang === "fa" ? course.name_fa : course.name_en })}
                          >
                            {t("common.delete")}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title={pendingDelete?.type === "major" ? t("admin.delete_major_confirm") : t("admin.delete_course_confirm")}
        description={pendingDelete?.name}
        confirmLabel={t("common.delete")}
        loading={deleting}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
