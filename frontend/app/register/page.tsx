"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Alert, Button, Card, Field, Input } from "@/components/ui";
import { useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/errors";
import { useLang } from "@/lib/lang-context";
import { validPassword, validUsername } from "@/lib/validation";

export default function RegisterPage() {
  const { api, signIn, setToken } = useAuth();
  const { t } = useLang();
  const router = useRouter();

  const [fullname, setFullname] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!fullname.trim()) next.fullname = t("auth.fill_all_fields");
    else if (fullname.trim().length > 150) next.fullname = t("validation.fullname_length");
    if (!validUsername(username.trim())) next.username = t("validation.username");
    if (!validPassword(password)) next.password = t("validation.password");
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setServerError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      const auth = await api.register(username.trim(), password, fullname.trim());
      // Token must exist BEFORE the /api/me call (see login page).
      setToken(auth.access_token);
      const me = await api.me();
      signIn(me.user, auth.access_token);
      router.replace("/app");
    } catch (err) {
      setServerError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm p-6">
        <h1 className="mb-4 text-center text-lg font-bold">{t("auth.register_title")}</h1>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {serverError && <Alert tone="error">{serverError}</Alert>}
          <Field label={t("auth.fullname")} htmlFor="reg-fullname" error={errors.fullname}>
            <Input
              id="reg-fullname"
              name="fullname"
              autoComplete="name"
              autoFocus
              value={fullname}
              onChange={(event) => setFullname(event.target.value)}
            />
          </Field>
          <Field label={t("auth.username")} htmlFor="reg-username" error={errors.username} hint={t("validation.username_hint")}>
            <Input
              id="reg-username"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </Field>
          <Field label={t("auth.password")} htmlFor="reg-password" error={errors.password} hint={t("validation.password_hint")}>
            <Input
              id="reg-password"
              name="password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <Button type="submit" loading={submitting} className="w-full">
            {t("auth.register_btn")}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400">
          {t("auth.have_account")}{" "}
          <Link href="/login" className="font-medium text-indigo-600 hover:underline dark:text-indigo-400">
            {t("auth.login_link")}
          </Link>
        </p>
      </Card>
    </main>
  );
}
