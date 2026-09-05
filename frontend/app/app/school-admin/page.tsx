"use client";

/** School Admin (TASK-038): institution-scoped class + membership
 * management. Same token-skinned primitives and data-fetching approach as
 * the site-admin page; the scope difference is the server contract — every
 * endpoint under /api/school/* filters by the actor's institution_id and
 * 403s cross-institution access, so the page never renders tenant state it
 * cannot act on. Gated on `role === "school_admin"` (UI gating only — the
 * API enforces authorization and returns 403, surfaced as an error alert). */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { School } from "lucide-react";

import { Alert, Badge, Button, Card, Field, Input, Select, Skeleton } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import type { SchoolClass, SchoolOverview, SchoolUser } from "@/types/api";

const isSchoolAdmin = (role?: string) => role === "school_admin";

export default function SchoolAdminPage() {
  const { user, api } = useAuth();
  const { t, lang } = useLang();
  const { showToast } = useToast();
  const router = useRouter();

  const [data, setData] = useState<SchoolOverview | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // new class form
  const [className, setClassName] = useState("");
  const [classGrade, setClassGrade] = useState("");
  const [creatingClass, setCreatingClass] = useState(false);

  // per-class edit state (one class being renamed at a time)
  const [editingClass, setEditingClass] = useState<SchoolClass | null>(null);
  const [editName, setEditName] = useState("");
  const [editGrade, setEditGrade] = useState("");
  const [savingClass, setSavingClass] = useState(false);

  const allowed = isSchoolAdmin(user?.role);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setData(await api.schoolOverview());
    } catch (err) {
      setLoadError(errorMessage(err));
      setData({ institution_id: 0, students: [], teachers: [], classes: [] });
    }
  }, [api]);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  useEffect(() => {
    // Signed-in non-school-admins: bounce quietly (middleware lets the
    // cookie through; the role check happens here and at the API).
    if (user && !allowed) router.replace("/app");
  }, [user, allowed, router]);

  if (!user) return null;

  async function createClass(event: React.FormEvent) {
    event.preventDefault();
    setActionError(null);
    if (!className.trim()) {
      setActionError(t("auth.fill_all_fields"));
      return;
    }
    setCreatingClass(true);
    try {
      await api.createSchoolClass({
        name: className.trim(),
        grade_level: classGrade.trim() || undefined,
      });
      setClassName("");
      setClassGrade("");
      showToast("success", t("profile.save_success"));
      await load();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setCreatingClass(false);
    }
  }

  function startEdit(klass: SchoolClass) {
    setEditingClass(klass);
    setEditName(klass.name);
    setEditGrade(klass.grade_level ?? "");
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editingClass) return;
    setActionError(null);
    if (!editName.trim()) {
      setActionError(t("auth.fill_all_fields"));
      return;
    }
    setSavingClass(true);
    try {
      await api.updateSchoolClass(editingClass.id, {
        name: editName.trim(),
        grade_level: editGrade.trim() || null,
      });
      setEditingClass(null);
      showToast("success", t("profile.save_success"));
      await load();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setSavingClass(false);
    }
  }

  async function assignMember(userId: number, classId: string) {
    setActionError(null);
    try {
      await api.assignSchoolUserClass(userId, { class_id: classId ? Number(classId) : null });
      showToast("success", t("profile.save_success"));
      await load();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  function memberRow(member: SchoolUser) {
    const label = member.fullname || member.username;
    return (
      <li key={member.id} className="flex items-center justify-between gap-3 rounded-control border border-border-subtle px-3 py-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-text-primary">{label}</p>
          <p className="truncate text-xs text-text-muted" dir="ltr">@{member.username}</p>
        </div>
        <div className="flex items-center gap-2">
          {member.role !== "student" && <Badge>{t(`school.${member.role === "teacher" ? "teachers" : "students"}`)}</Badge>}
          <Select
            aria-label={t("school.assign_class")}
            value={member.class_id != null ? String(member.class_id) : ""}
            onChange={(event) => void assignMember(member.id, event.target.value)}
          >
            <option value="">{t("school.unassigned")}</option>
            {(data?.classes ?? []).map((klass) => (
              <option key={klass.id} value={klass.id}>
                {klass.name}
              </option>
            ))}
          </Select>
        </div>
      </li>
    );
  }

  if (!allowed) return null;

  return (
    <div className="space-y-6">
      <div>
        <p className="flex items-center gap-1.5 text-[11px] font-medium text-text-muted">
          <School size={12} aria-hidden className="text-accent" />
          {lang === "fa" ? "منطقه مدرسه" : "School zone"}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-text-primary">{t("school.title")}</h1>
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

      {!data && !loadError && (
        <Card className="space-y-2 p-5">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-8 w-full" />
          ))}
        </Card>
      )}

      {data && (
        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("school.classes")}</h2>
            <form onSubmit={createClass} className="space-y-3 border-b border-border-subtle pb-5">
              <Field label={t("school.class_name")} htmlFor="school-class-name">
                <Input id="school-class-name" value={className} onChange={(event) => setClassName(event.target.value)} dir="auto" />
              </Field>
              <Field label={t("school.grade_optional")} htmlFor="school-class-grade">
                <Input id="school-class-grade" value={classGrade} onChange={(event) => setClassGrade(event.target.value)} dir="auto" />
              </Field>
              <Button type="submit" loading={creatingClass}>
                + {t("common.create")}
              </Button>
            </form>
            <ul className="mt-4 space-y-2">
              {data.classes.length === 0 ? (
                <li className="text-xs text-text-muted">{t("school.no_classes")}</li>
              ) : (
                data.classes.map((klass) => (
                  <li key={klass.id} className="flex items-center justify-between rounded-control border border-border-subtle px-3 py-2">
                    <div className="min-w-0">
                      {editingClass?.id === klass.id ? (
                        <form onSubmit={saveEdit} className="flex items-center gap-2" dir="auto">
                          <Input value={editName} onChange={(event) => setEditName(event.target.value)} className="h-8 w-40" />
                          <Input value={editGrade} onChange={(event) => setEditGrade(event.target.value)} className="h-8 w-24" placeholder={t("school.grade")} />
                          <Button type="submit" size="sm" loading={savingClass}>{t("common.save")}</Button>
                          <Button type="button" variant="ghost" size="sm" onClick={() => setEditingClass(null)}>{t("common.cancel")}</Button>
                        </form>
                      ) : (
                        <>
                          <p className="truncate text-sm font-medium text-text-primary">{klass.name}</p>
                          <p className="text-xs text-text-muted" dir="auto">
                            {klass.grade_level ? `${t("school.grade")}: ${klass.grade_level}` : t("school.no_class")}
                          </p>
                        </>
                      )}
                    </div>
                    {editingClass?.id !== klass.id && (
                      <Button variant="ghost" size="sm" onClick={() => startEdit(klass)}>
                        {t("common.edit")}
                      </Button>
                    )}
                  </li>
                ))
              )}
            </ul>
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("school.students")}</h2>
            {data.students.length === 0 ? (
              <p className="text-xs text-text-muted">{t("school.no_students")}</p>
            ) : (
              <ul className="space-y-2">{data.students.map(memberRow)}</ul>
            )}
            <h2 className="mb-3 mt-6 text-base font-semibold text-text-primary">{t("school.teachers")}</h2>
            {data.teachers.length === 0 ? (
              <p className="text-xs text-text-muted">{t("school.no_teachers")}</p>
            ) : (
              <ul className="space-y-2">{data.teachers.map(memberRow)}</ul>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
