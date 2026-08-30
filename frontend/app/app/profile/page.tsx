"use client";

/** Profile: view identity, edit fullname, change password. Theme is
 * toggled from the app shell (server-backed); password change revokes all
 * refresh tokens server-side — the current tab's refresh cookie is
 * rotated out, but the signed-in session survives (access token still
 * valid; next refresh gets a new pair). */

import { useState, type FormEvent } from "react";

import { Alert, Button, Card, Field, Input } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { useLang } from "@/lib/lang-context";
import { validPassword } from "@/lib/validation";

export default function ProfilePage() {
  const { user, api, refreshUser } = useAuth();
  const { t, lang } = useLang();

  const [fullname, setFullname] = useState(user?.fullname ?? "");
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setProfileError(null);
    setProfileSuccess(false);
    if (!fullname.trim() || fullname.trim().length > 150) {
      setProfileError(t("validation.fullname_length"));
      return;
    }
    setSavingProfile(true);
    try {
      await api.updateMe({ fullname: fullname.trim() });
      setProfileSuccess(true);
      await refreshUser();
    } catch (err) {
      setProfileError(errorMessage(err));
    } finally {
      setSavingProfile(false);
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);
    if (!validPassword(newPassword)) {
      setPasswordError(t("validation.password"));
      return;
    }
    setSavingPassword(true);
    try {
      await api.updateMe({ current_password: currentPassword, password: newPassword });
      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setPasswordError(errorMessage(err));
    } finally {
      setSavingPassword(false);
    }
  }

  if (!user) return null;

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-xl font-bold">{t("profile.title")}</h1>

      <Card className="space-y-1 p-5 text-sm">
        <p>
          <span className="font-medium">{t("auth.username")}:</span> {user.username}
        </p>
        <p>
          <span className="font-medium">{t("auth.fullname")}:</span> {user.fullname}
        </p>
        <p className="text-slate-500 dark:text-slate-400">
          {t("profile.member_since")}: {formatDateTime(user.created_at, lang)}
        </p>
      </Card>

      <Card className="p-5">
        <h2 className="mb-3 text-base font-semibold">{t("auth.fullname")}</h2>
        <form onSubmit={saveProfile} className="space-y-3" noValidate>
          {profileSuccess && <Alert tone="success">{t("profile.save_success")}</Alert>}
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
        <h2 className="mb-1 text-base font-semibold">{t("profile.change_password")}</h2>
        <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">{t("profile.password_change_note")}</p>
        <form onSubmit={savePassword} className="space-y-3" noValidate>
          {passwordSuccess && <Alert tone="success">{t("profile.save_success")}</Alert>}
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
