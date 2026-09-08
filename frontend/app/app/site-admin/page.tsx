"use client";

/** Site Admin (TASK-039): global dashboard — institutions with counts,
 * tenant + first-admin creation, plan_tier editing, and the global audit
 * log. Mirrors /app/school-admin's structure: token-skinned primitives,
 * useAuth().api fetching, toasts. No institution filtering anywhere —
 * the site-level roles are global; the API enforces authorization
 * (school_admin gets 403 on every /api/site/* endpoint) and this page
 * surfaces it as an error alert. Gated on `role === "site_admin"` (UI
 * gating only). Since TASK-041 the institution card is shared with
 * /app/support, which holds the same permission level. */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Globe } from "lucide-react";

import { Alert, Badge, Button, Card, Input, Select, Skeleton } from "@/components/ui";
import { SiteInstitutionsCard } from "@/components/site-institutions-card";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import type { AuditEntry, SiteInstitution } from "@/types/api";

const isSiteAdmin = (role?: string) => role === "site_admin";

export default function SiteAdminPage() {
  const { user, api } = useAuth();
  const { t, lang } = useLang();
  const router = useRouter();

  const [institutions, setInstitutions] = useState<SiteInstitution[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

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

      {actionError && <Alert tone="error">{actionError}</Alert>}

      <div className="grid gap-6 xl:grid-cols-2">
        <SiteInstitutionsCard
          institutions={institutions}
          loadError={loadError}
          onRetry={() => void load()}
          onActionError={setActionError}
          onChanged={async () => {
            await load();
            await loadAudit(auditPage);
          }}
        />

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
    </div>
  );
}
