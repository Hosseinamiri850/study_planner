"use client";

/** Authenticated app chrome: top navigation with user identity, theme
 * toggle, language switch, admin link (gated by is_admin — UI gating
 * only; the API enforces), and logout. Responsive: nav collapses to a
 * mobile menu under md. */

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/auth-context";
import { useLang } from "@/lib/lang-context";
import { useTheme } from "@/lib/theme-context";
import { Button } from "./ui";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useLang();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const navLink = (href: string, label: string) => {
    const active = pathname === href || (href !== "/app" && pathname.startsWith(href));
    return (
      <Link
        key={href}
        href={href}
        onClick={() => setMenuOpen(false)}
        className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
          active
            ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300"
            : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
        }`}
      >
        {label}
      </Link>
    );
  };

  const controls = (
    <div className="flex items-center gap-2">
      <select
        aria-label={t("common.language")}
        value={lang}
        onChange={(event) => setLang(event.target.value as "fa" | "en")}
        className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-800"
      >
        <option value="fa">فا</option>
        <option value="en">EN</option>
      </select>
      <Button variant="ghost" onClick={toggle} aria-label={t("common.toggle_theme")} className="px-2 py-1 text-xs">
        {theme === "dark" ? "☀️" : "🌙"}
      </Button>
      <Button variant="secondary" onClick={() => void logout()} className="px-3 py-1 text-xs">
        {t("nav.logout")}
      </Button>
    </div>
  );

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <Link href="/app" className="text-base font-bold text-indigo-600 dark:text-indigo-400">
              {t("app_name")}
            </Link>
            <nav className="hidden items-center gap-1 md:flex" aria-label={t("a11y.main_nav")}>
              {navLink("/app", t("nav.dashboard"))}
              {user?.is_admin && navLink("/app/admin", t("nav.admin_panel"))}
              {navLink("/app/profile", t("profile.title"))}
            </nav>
          </div>
          <div className="hidden items-center gap-3 md:flex">
            {user && (
              <span className="text-sm text-slate-600 dark:text-slate-300">{user.fullname}</span>
            )}
            {controls}
          </div>
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-label={t("a11y.menu")}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 md:hidden dark:text-slate-300 dark:hover:bg-slate-700"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        {menuOpen && (
          <nav className="flex flex-col gap-1 border-t border-slate-200 px-4 py-2 md:hidden dark:border-slate-700" aria-label={t("a11y.mobile_nav")}>
            {navLink("/app", t("nav.dashboard"))}
            {user?.is_admin && navLink("/app/admin", t("nav.admin_panel"))}
            {navLink("/app/profile", t("profile.title"))}
            <div className="flex items-center justify-between py-1">
              {user && <span className="text-sm text-slate-600 dark:text-slate-300">{user.fullname}</span>}
              {controls}
            </div>
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
