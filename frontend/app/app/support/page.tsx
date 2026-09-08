"use client";

/** Support Console (TASK-040): global READ-ONLY visibility — institutions
 * with counts, user search across B2C + all tenants, the global audit
 * log — plus the one deliberate exception: impersonation. Clicking
 * "Impersonate" mints a short-lived token as that user and swaps the SPA
 * session to it (in-memory; a reload ends it, like the token). Every
 * action taken under the impersonated token is audited with the agent's
 * id server-side; admin surfaces reject impersonation tokens outright.
 * Gated on `role === "support"` (UI gating only — the API enforces). */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Headset } from "lucide-react";

import { Alert, Badge, Button, Card, Input, Skeleton } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import type { AuditEntry, SiteInstitution, SupportUser } from "@/types/api";

const isSupport = (role?: string) => role === "support";

export default function SupportPage() {
  const { user, api, beginImpersonation } = useAuth();
  const { t, lang } = useLang();
  const { showToast } = useToast();
  const router = useRouter();

  const [institutions, setInstitutions] = useState<SiteInstitution[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // user search
  const [searchQuery, setSearchQuery] = useState("");
  const [users, setUsers] = useState<SupportUser[] | null>(null);
  const [usersPage, setUsersPage] = useState(1);
  const [usersPages, setUsersPages] = useState(1);
  const [usersTotal, setUsersTotal] = useState(0);
  const [impersonatingId, setImpersonatingId] = useState<number | null>(null);

  // audit log
  const [audit, setAudit] = useState<{ entries: AuditEntry[]; page: number; pages: number; total: number } | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [filterInstitution, setFilterInstitution] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [filterActor, setFilterActor] = useState("");
  const [auditPage, setAuditPage] = useState(1);

  const allowed = isSupport(user?.role);

  const loadInstitutions = useCallback(async () => {
    setLoadError(null);
    try {
      setInstitutions((await api.supportInstitutions()).institutions);
    } catch (err) {
      setLoadError(errorMessage(err));
      setInstitutions([]);
    }
  }, [api]);

  const loadUsers = useCallback(async (page: number, query: string) => {
    try {
      const data = await api.supportUsers({ query: query || undefined, page, per_page: 10 });
      setUsers(data.users);
      setUsersPage(data.page);
      setUsersPages(data.pages);
      setUsersTotal(data.total);
    } catch (err) {
      setActionError(errorMessage(err));
      setUsers([]);
    }
  }, [api]);

  const loadAudit = useCallback(async (page: number) => {
    setAuditError(null);
    try {
      const data = await api.supportAuditLog({
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
    if (allowed) void loadInstitutions();
  }, [allowed, loadInstitutions]);

  useEffect(() => {
    if (user && !allowed) router.replace("/app");
  }, [user, allowed, router]);

  useEffect(() => {
    if (allowed) void loadUsers(usersPage, searchQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allowed, usersPage]);

  useEffect(() => {
    if (allowed) void loadAudit(auditPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allowed, auditPage, filterInstitution, filterAction, filterActor]);

  if (!user) return null;

  async function impersonate(target: SupportUser) {
    setActionError(null);
    setImpersonatingId(target.id);
    try {
      const result = await api.impersonate(target.id);
      // Adopt the impersonated identity; the shell banner takes over.
      beginImpersonation(
        {
          id: result.user.id,
          username: result.user.username,
          fullname: result.user.fullname,
          is_admin: result.user.role === "site_admin",
          theme: "dark",
          created_at: result.user.created_at ?? "",
          role: result.user.role,
        },
        result.access_token,
      );
      showToast("success", t("profile.save_success"));
      router.replace("/app");
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setImpersonatingId(null);
    }
  }

  if (!allowed) return null;

  return (
    <div className="space-y-6">
      <div>
        <p className="flex items-center gap-1.5 text-[11px] font-medium text-text-muted">
          <Headset size={12} aria-hidden className="text-accent" />
          {lang === "fa" ? "منطقه پشتیبانی" : "Support zone"}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-text-primary">{t("support.title")}</h1>
        <p className="mt-1 text-xs text-text-muted">{t("support.read_only_note")}</p>
      </div>

      {loadError && (
        <Alert tone="error">
          {loadError}{" "}
          <Button variant="secondary" size="sm" className="ms-2" onClick={() => void loadInstitutions()}>
            {t("common.retry")}
          </Button>
        </Alert>
      )}
      {actionError && <Alert tone="error">{actionError}</Alert>}

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
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("support.institutions")}</h2>
            {institutions.length === 0 ? (
              <p className="text-xs text-text-muted">{t("site.no_institutions")}</p>
            ) : (
              <ul className="space-y-2">
                {institutions.map((institution) => (
                  <li key={institution.id} className="flex items-center justify-between rounded-control border border-border-subtle px-3 py-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-text-primary" dir="auto">{institution.name}</p>
                      <p className="text-xs text-text-muted" dir="auto">
                        <Badge>{institution.type}</Badge> {institution.plan_tier}
                      </p>
                    </div>
                    <p className="text-xs text-text-muted" dir="auto">
                      {institution.students} {t("site.students")} · {institution.classes} {t("site.classes")}
                    </p>
                  </li>
                ))}
              </ul>
            )}

            <h2 className="mb-3 mt-6 text-base font-semibold text-text-primary">{t("support.users")}</h2>
            <Input
              aria-label={t("support.search_users")}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  setUsersPage(1);
                  void loadUsers(1, searchQuery);
                }
              }}
              placeholder={t("support.search_users")}
              dir="auto"
            />
            <div className="mt-2 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => { setUsersPage(1); void loadUsers(1, searchQuery); }}>
                {lang === "fa" ? "جستجو" : "Search"}
              </Button>
            </div>
            {!users && <Skeleton className="mt-3 h-24 w-full" />}
            {users && (
              users.length === 0 ? (
                <p className="mt-3 text-xs text-text-muted">{t("support.no_users")}</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {users.map((u) => (
                    <li key={u.id} className="flex items-center justify-between gap-2 rounded-control border border-border-subtle px-3 py-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-text-primary">{u.fullname || u.username}</p>
                        <p className="truncate text-xs text-text-muted" dir="ltr">@{u.username} · {u.role} · inst:{u.institution_id ?? "—"}</p>
                      </div>
                      <Button
                        variant="secondary"
                        size="sm"
                        loading={impersonatingId === u.id}
                        onClick={() => void impersonate(u)}
                      >
                        {t("support.impersonate")}
                      </Button>
                    </li>
                  ))}
                </ul>
              )
            )}
            {users && usersPages > 1 && (
              <div className="mt-3 flex items-center justify-between">
                <Button variant="secondary" size="sm" disabled={usersPage <= 1} onClick={() => setUsersPage(usersPage - 1)}>
                  {t("support.prev")}
                </Button>
                <span className="text-xs text-text-muted">{t("support.page_of", { page: usersPage, pages: usersPages, total: usersTotal })}</span>
                <Button variant="secondary" size="sm" disabled={usersPage >= usersPages} onClick={() => setUsersPage(usersPage + 1)}>
                  {t("support.next")}
                </Button>
              </div>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="mb-3 text-base font-semibold text-text-primary">{t("support.audit_log")}</h2>
            <div className="mb-4 grid grid-cols-3 gap-2">
              <Input
                aria-label={t("support.filter_institution")}
                value={filterInstitution}
                onChange={(event) => { setAuditPage(1); setFilterInstitution(event.target.value); }}
                placeholder={t("support.filter_institution")}
                dir="ltr"
                inputMode="numeric"
              />
              <Input
                aria-label={t("support.filter_action")}
                value={filterAction}
                onChange={(event) => { setAuditPage(1); setFilterAction(event.target.value); }}
                placeholder={t("support.filter_action")}
                dir="ltr"
              />
              <Input
                aria-label={t("support.filter_actor")}
                value={filterActor}
                onChange={(event) => { setAuditPage(1); setFilterActor(event.target.value); }}
                placeholder={t("support.filter_actor")}
                dir="ltr"
                inputMode="numeric"
              />
            </div>
            {auditError && <Alert tone="error">{auditError}</Alert>}
            {!audit && !auditError && <Skeleton className="h-40 w-full" />}
            {audit && (
              audit.entries.length === 0 ? (
                <p className="text-xs text-text-muted">{t("support.no_audit")}</p>
              ) : (
                <ul className="space-y-2">
                  {audit.entries.map((entry) => (
                    <li key={entry.id} className="rounded-control border border-border-subtle px-3 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium text-text-primary" dir="ltr">{entry.action}</p>
                        <Badge>{entry.created_at ? new Date(entry.created_at).toLocaleString(lang === "fa" ? "fa-IR" : "en-GB") : "—"}</Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-text-muted" dir="ltr">
                        #{entry.id} · {entry.target_type}:{entry.target_id ?? "—"} · actor:{entry.actor_user_id ?? "—"}
                        {entry.impersonator_id != null ? ` · ${lang === "fa" ? "پشتیبان" : "support"}:${entry.impersonator_id}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              )
            )}
            {audit && audit.pages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <Button variant="secondary" size="sm" disabled={auditPage <= 1} onClick={() => setAuditPage(auditPage - 1)}>
                  {t("support.prev")}
                </Button>
                <span className="text-xs text-text-muted">{t("support.page_of", { page: audit.page, pages: audit.pages, total: audit.total })}</span>
                <Button variant="secondary" size="sm" disabled={auditPage >= audit.pages} onClick={() => setAuditPage(auditPage + 1)}>
                  {t("support.next")}
                </Button>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
