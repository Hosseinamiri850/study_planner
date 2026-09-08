"use client";

/** Site Admin (TASK-039): global dashboard — institutions with counts,
 * tenant + first-admin creation, plan_tier editing, and the global audit
 * log. Mirrors /app/school-admin's structure: token-skinned primitives,
 * useAuth().api fetching, toasts. No institution filtering anywhere — the
 * site_admin role is global; the API enforces authorization (school_admin
 * gets 403 on every /api/site/* endpoint) and this page surfaces it as an
 * error alert. Gated on `role === "site_admin"` (UI gating only). */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Globe } from "lucide-react";

import { Alert, Badge, Button, Card, Field, Input, Select, Skeleton } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import type { AuditEntry, PlanTier, SiteInstitution } from "@/types/api";

const isSiteAdmin = (role?: string) => role === "site_admin";
const PLAN_TIERS: PlanTier[] = ["free", "pro", "enterprise"];
const INSTITUTION_TYPES = ["school", "university", "academy"];

export default function SiteAdminPage() {
  const { user, api } = useAuth();
  const { t, lang } = useLang();
  const { showToast } = useToast();
  const router = useRouter();

  const [institutions, setInstitutions] = useState<SiteInstitution[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [createdNote, setCreatedNote] = useState<string | null>(null);

  // create-institution form
  const [instName, setInstName] = useState("");
  const [instType, setInstType] = useState("school");
  const [instTier, setInstTier] = useState<PlanTier>("free");
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [adminFullname, setAdminFullname] = useState("");
  const [creating, setCreating] = useState(false);

  // plan tier editing: one institution saved at a time
  const [tierDraft, setTierDraft] = useState<Record<number, PlanTier>>({});
  const [savingTierId, setSavingTierId] = useState<number | null>(null);

  // audit log
  const [audit, setAudit] = useState<{ entries: AuditEntry[]; page: number; pages: number; total: number } | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [filterInstitution, setFilterInstitution] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterActor, setFilterActor] = useState("");
  const [auditPage, setAuditPage] = useState(1);

  const allowed = isSiteAdmin(user?.role);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setInstitutions((await api.siteInstitutions()).institutions);
    } catch (err) {
      setLoadError(errorMessage(err));
      setInstitutions([]);
    }
  }, [api]);

  const loadAudit = useCallback(async (page: number) => {
    setAuditError(null);
    try {
      const data = await api.siteAuditLog({
        institution_id: filterInstitution ? Number(filterInstitution) : undefined,
        action: filterAction || undefined,
        actor_user_id: filterActor ? Number(filterActor) : undefined,
        page,
        per_page: 10,
      });
      setAudit(data);
      setAuditPage(data.page);
    } catch (err) {
      setAuditError(errorMessage(err));
      setAudit({ entries: [], page: 1, pages: 1, total: 0 });
    }
  }, [api, filterInstitution, filterAction, filterActor]);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  useEffect(() => {
    if (user && !allowed) router.replace("/app");
  }, [user, allowed, router]);

  useEffect(() => {
    if (allowed) void loadAudit(auditPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allowed, auditPage, filterInstitution, filterAction, filterActor]);

  if (!user) return null;

  async function createInstitution(event: React.FormEvent) {
    event.preventDefault();
    setActionError(null);
    setCreatedNote(null);
    if (!instName.trim() || !adminUsername.trim() || adminPassword.length < 8) {
      setActionError(t("auth.fill_all_fields"));
      return;
    }
    setCreating(true);
    try {
      const result = await api.createSiteInstitution({
        name: instName.trim(),
        type: instType,
        plan_tier: instTier,
        admin_username: adminUsername.trim(),
        admin_password: adminPassword,
        admin_fullname: adminFullname.trim() || undefined,
      });
      setCreatedNote(`${t("site.created_admin_note")} (${result.admin.username})`);
      setInstName("");
      setAdminUsername("");
      setAdminPassword("");
      setAdminFullname("");
      showToast("success", t("profile.save_success"));
      await load();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function saveTier(institution: SiteInstitution) {
    const next = tierDraft[institution.id] ?? (institution.plan_tier as PlanTier);
    setActionError(null);
    setSavingTierId(institution.id);
    try {
      await api.updateInstitutionPlanTier(institution.id, next);
      showToast("success", t("profile.save_success"));
      await load();
      await loadAudit(auditPage);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setSavingTierId(null);
    }
  }

  if (!allowed) return null;

  return (
    <div className="space-y-6">
      <div>
        <p className="flex items-center gap-1.5 text-[11px] font-medium text-text-muted">
          <Globe size={12} aria-hidden className="text-accent" />
          {lang === "fa" ? "منطقه سایت" : "Site zone"}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-text-primary">{t("site.title")}</h1>
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
      {createdNote && <Alert tone="success">{createdNote}</Alert>}

      {!institutions && !loadError && (
        <Card className="space-y-2 p-5">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-8 w-full" />
          ))}
        </Card>
      )}

      {institutions && (
        <div className="grid gap-6 xl:grid-cols-2">
          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("site.institutions")}</h2>
            {institutions.length === 0 ? (
              <p className="text-xs text-text-muted">{t("site.no_institutions")}</p>
            ) : (
              <ul className="space-y-2">
                {institutions.map((institution) => {
                  const draft = tierDraft[institution.id] ?? (institution.plan_tier as PlanTier);
                  const dirty = draft !== institution.plan_tier;
                  return (
                    <li key={institution.id} className="space-y-2 rounded-control border border-border-subtle px-3 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-text-primary" dir="auto">{institution.name}</p>
                          <p className="text-xs text-text-muted" dir="auto">
                            <Badge>{institution.type}</Badge> {institution.students} {t("site.students")} · {institution.teachers} {t("site.teachers")} · {institution.classes} {t("site.classes")}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Select
                            aria-label={t("site.plan_tier")}
                            value={draft}
                            onChange={(event) => setTierDraft((prev) => ({ ...prev, [institution.id]: event.target.value as PlanTier }))}
                            className="h-9 w-32"
                          >
                            {PLAN_TIERS.map((tier) => (
                              <option key={tier} value={tier}>{tier}</option>
                            ))}
                          </Select>
                          <Button size="sm" disabled={!dirty} loading={savingTierId === institution.id} onClick={() => void saveTier(institution)}>
                            {t("common.save")}
                          </Button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            <form onSubmit={createInstitution} className="mt-5 space-y-3 border-t border-border-subtle pt-5">
              <h3 className="text-sm font-semibold text-text-secondary">{t("site.create_institution")}</h3>
              <Field label={t("site.inst_name")} htmlFor="site-inst-name">
                <Input id="site-inst-name" value={instName} onChange={(event) => setInstName(event.target.value)} dir="auto" />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("site.inst_type")} htmlFor="site-inst-type">
                  <Select id="site-inst-type" value={instType} onChange={(event) => setInstType(event.target.value)}>
                    {INSTITUTION_TYPES.map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </Select>
                </Field>
                <Field label={t("site.plan_tier")} htmlFor="site-inst-tier">
                  <Select id="site-inst-tier" value={instTier} onChange={(event) => setInstTier(event.target.value as PlanTier)}>
                    {PLAN_TIERS.map((tier) => (
                      <option key={tier} value={tier}>{tier}</option>
                    ))}
                  </Select>
                </Field>
              </div>
              <p className="text-xs font-semibold text-text-secondary">{t("site.first_admin")}</p>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t("site.admin_username")} htmlFor="site-admin-username">
                  <Input id="site-admin-username" value={adminUsername} onChange={(event) => setAdminUsername(event.target.value)} dir="ltr" autoComplete="off" />
                </Field>
                <Field label={t("site.admin_fullname")} htmlFor="site-admin-fullname">
                  <Input id="site-admin-fullname" value={adminFullname} onChange={(event) => setAdminFullname(event.target.value)} dir="auto" />
                </Field>
              </div>
              <Field label={t("site.admin_password")} htmlFor="site-admin-password">
                <Input id="site-admin-password" type="password" value={adminPassword} onChange={(event) => setAdminPassword(event.target.value)} dir="ltr" autoComplete="new-password" />
              </Field>
              <Button type="submit" loading={creating}>
                + {t("common.create")}
              </Button>
            </form>
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("site.audit_log")}</h2>
            <div className="mb-4 grid grid-cols-3 gap-2">
              <Select aria-label={t("site.filter_institution")} value={filterInstitution} onChange={(event) => { setAuditPage(1); setFilterInstitution(event.target.value); }}>
                <option value="">{t("site.all_institutions")}</option>
                {(institutions ?? []).map((institution) => (
                  <option key={institution.id} value={institution.id}>{institution.name}</option>
                ))}
              </Select>
              <Input
                aria-label={t("site.filter_action")}
                value={filterAction}
                onChange={(event) => { setAuditPage(1); setFilterAction(event.target.value); }}
                placeholder={t("site.filter_action")}
                dir="ltr"
              />
              <Input
                aria-label={t("site.filter_actor")}
                value={filterActor}
                onChange={(event) => { setAuditPage(1); setFilterActor(event.target.value); }}
                placeholder={t("site.filter_actor")}
                dir="ltr"
                inputMode="numeric"
              />
            </div>
            {auditError && <Alert tone="error">{auditError}</Alert>}
            {!audit && !auditError && <Skeleton className="h-40 w-full" />}
            {audit && (
              audit.entries.length === 0 ? (
                <p className="text-xs text-text-muted">{t("site.no_audit")}</p>
              ) : (
                <ul className="space-y-2">
                  {audit.entries.map((entry) => (
                    <li key={entry.id} className="rounded-control border border-border-subtle px-3 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium text-text-primary" dir="ltr">{entry.action}</p>
                        <Badge>{entry.created_at ? new Date(entry.created_at).toLocaleString(lang === "fa" ? "fa-IR" : "en-GB") : "—"}</Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-text-muted" dir="ltr">
                        #{entry.id} · {entry.target_type}:{entry.target_id ?? "—"} · inst:{entry.institution_id ?? "—"} · actor:{entry.actor_user_id ?? "—"}
                      </p>
                    </li>
                  ))}
                </ul>
              )
            )}
            {audit && audit.pages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <Button variant="secondary" size="sm" disabled={auditPage <= 1} onClick={() => setAuditPage(auditPage - 1)}>
                  {t("site.prev")}
                </Button>
                <span className="text-xs text-text-muted">{t("site.page_of", { page: audit.page, pages: audit.pages, total: audit.total })}</span>
                <Button variant="secondary" size="sm" disabled={auditPage >= audit.pages} onClick={() => setAuditPage(auditPage + 1)}>
                  {t("site.next")}
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
