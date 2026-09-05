"use client";

/** Profile (Phase 5): identity header (avatar block + member since), then
 * fullname and password forms. Save feedback via toast; page alerts only
 * for blocking errors. Password change revokes all refresh tokens
 * server-side — the signed-in session survives (access token still valid;
 * next refresh gets a new pair). */

import { useState, type FormEvent } from "react";

import { Alert, Button, Card, Field, Input } from "@/components/ui";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useLang } from "@/lib/lang-context";
import { validPassword } from "@/lib/validation";

export default function ProfilePage() {
  const { user, api, refreshUser } = useAuth();
  const { t, lang } = useLang();
  const { showToast } = useToast();

  const [fullname, setFullname] = useState(user?.fullname ?? "");
  const [profileError, setProfileError] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [savingPassword, setSavingPassword] = useState(false);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setProfileError(null);
    if (!fullname.trim() || fullname.trim().length > 150) {
      setProfileError(t("validation.fullname_length"));
      return;
    }
    setSavingProfile(true);
    try {
      await api.updateMe({ fullname: fullname.trim() });
      await refreshUser();
      showToast("success", t("profile.save_success"));
    } catch (err) {
      setProfileError(errorMessage(err));
    } finally {
      setSavingProfile(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    if (!validPassword(newPassword)) {
      setPasswordError(t("validation.password"));
      return;
    }
    setSavingPassword(true);
    try {
      await api.updateMe({ current_password: currentPassword, password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      showToast("success", t("profile.save_success"));
    } catch (err) {
      setPasswordError(errorMessage(err));
    } finally {
      setSavingPassword(false);
    }
  }

  if (!user) return null;

  const initials = (user.fullname || user.username)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div>
        <p className="tracking-label text-[11px] font-medium text-text-muted">
          {lang === "fa" ? "حساب کاربری" : "Account"}
        </p>
        <h1 className="mt-0.5 text-xl font-bold text-text-primary">{t("profile.title")}</h1>
      </div>

      {/* Identity header */}
      <div className="flex items-center gap-4">
        <span
          aria-hidden
          className="flex h-14 w-14 shrink-0 items-center justify-center rounded-pill bg-accent-soft text-lg font-bold text-accent"
        >
          {initials}
        </span>
        <div className="min-w-0">
          <p className="truncate text-base font-semibold text-text-primary">{user.fullname || user.username}</p>
          <p className="truncate text-sm text-text-muted">
            @{user.username} · {t("profile.member_since")}: {formatDateTime(user.created_at, lang)}
          </p>
        </div>
      </div>

      <Card className="p-5">
        <h2 className="mb-3 text-base font-semibold text-text-primary">{t("auth.fullname")}</h2>
        <form onSubmit={saveProfile} className="space-y-3" noValidate>
          {profileError && <Alert tone="error">{profileError}</Alert>}
          <Field label={t("auth.fullname")} htmlFor="profile-fullname">
            <Input id="profile-fullname" value={fullname} onChange={(event) => setFullname(event.target.value)} maxLength={150} />
          </Field>
          <Button type="submit" loading={savingProfile}>
            {t("common.save")}
          </Button>
        </form>
      </Card>

      <Card className="p-5">
        <h2 className="text-base font-semibold text-text-primary">{t("profile.change_password")}</h2>
        <p className="mb-3 mt-1 text-xs text-text-muted">{t("profile.password_change_note")}</p>
        <form onSubmit={savePassword} className="space-y-3" noValidate>
          {passwordError && <Alert tone="error">{passwordError}</Alert>}
          <Field label={t("profile.current_password")} htmlFor="profile-current-password">
            <Input
              id="profile-current-password"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </Field>
          <Field label={t("profile.new_password")} htmlFor="profile-new-password" hint={t("validation.password_hint")}>
            <Input
              id="profile-new-password"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </Field>
          <Button type="submit" loading={savingPassword}>
            {t("common.save")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
