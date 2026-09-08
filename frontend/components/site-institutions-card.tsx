"use client";

/** Shared institution-management card (TASK-041): institutions with
 * counts, plan_tier editing, and the one-request tenant+first-admin
 * creation form. Rendered by both /app/site-admin and /app/support —
 * support gained site_admin permission parity by product decision, so
 * one card serves both dashboards instead of duplicating UI. The API
 * (site_admin_required) enforces who may call these endpoints; this
 * component is presentation + form state only. */

import { useState } from "react";

import { Alert, Badge, Button, Card, Field, Input, Select, Skeleton } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import type { PlanTier, SiteInstitution } from "@/types/api";

const PLAN_TIERS: PlanTier[] = ["free", "pro", "enterprise"];
const INSTITUTION_TYPES = ["school", "university", "academy"];

interface SiteInstitutionsCardProps {
  institutions: SiteInstitution[] | null;
  loadError: string | null;
  onRetry: () => void;
  onActionError: (message: string | null) => void;
  /** Refetch after a successful create/tier-save. */
  onChanged: () => void | Promise<void>;
}

export function SiteInstitutionsCard({ institutions, loadError, onRetry, onActionError, onChanged }: SiteInstitutionsCardProps) {
  const { api } = useAuth();
  const { t } = useLang();
  const { showToast } = useToast();

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

  async function createInstitution(event: React.FormEvent) {
    event.preventDefault();
    onActionError(null);
    setCreatedNote(null);
    if (!instName.trim() || !adminUsername.trim() || adminPassword.length < 8) {
      onActionError(t("auth.fill_all_fields"));
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
      await onChanged();
    } catch (err) {
      onActionError(errorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function saveTier(institution: SiteInstitution) {
    const next = tierDraft[institution.id] ?? (institution.plan_tier as PlanTier);
    onActionError(null);
    setSavingTierId(institution.id);
    try {
      await api.updateInstitutionPlanTier(institution.id, next);
      showToast("success", t("profile.save_success"));
      await onChanged();
    } catch (err) {
      onActionError(errorMessage(err));
    } finally {
      setSavingTierId(null);
    }
  }

  return (
    <Card className="p-5">
      <h2 className="mb-3 text-base font-semibold text-text-primary">{t("site.institutions")}</h2>
      {loadError && (
        <Alert tone="error">
          {loadError}{" "}
          <Button variant="secondary" size="sm" className="ms-2" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        </Alert>
      )}
      {createdNote && <Alert tone="success">{createdNote}</Alert>}
      {!institutions && !loadError && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-8 w-full" />
          ))}
        </div>
      )}
      {institutions && (
        institutions.length === 0 ? (
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
        )
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
  );
}
