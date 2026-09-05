"use client";

/** Authenticated app chrome, rebuilt on the token layer (Phase 3):
 * logomark + wordmark, primary nav, UserMenu (avatar + dropdown), segmented
 * language control, icon theme toggle. Mobile: Radix Dialog sheet with an
 * identity block. Admin link is gated on is_admin (UI gating only — the
 * API enforces). */

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import { Menu, MoonStar, SunMedium, X } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { useLang } from "@/lib/lang-context";
import { useTheme } from "@/lib/theme-context";
import { LangSwitch } from "./lang-switch";
import { Logomark } from "./logomark";
import { UserMenu } from "./user-menu";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { t } = useLang();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navItems = [
    { href: "/app", label: t("nav.dashboard") },
    ...(user?.is_admin ? [{ href: "/app/admin", label: t("nav.admin_panel") }] : []),
    { href: "/app/profile", label: t("profile.title") },
  ];

  const isNavActive = (href: string) =>
    pathname === href || (href !== "/app" && pathname.startsWith(href));

  const navLinkClass = (active: boolean) =>
    `rounded-control px-3 py-1.5 text-sm font-medium transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
      active
        ? "bg-accent-soft text-accent"
        : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
    }`;

  const navLinks = (onNavigate?: () => void) => (
    <>
      {navItems.map(({ href, label }) => (
        <Link
          key={href}
          href={href}
          onClick={onNavigate}
          aria-current={isNavActive(href) ? "page" : undefined}
          className={navLinkClass(isNavActive(href))}
        >
          {label}
        </Link>
      ))}
    </>
  );

  const themeToggle = (extraClass = "") => (
    <button
      type="button"
      onClick={toggle}
      aria-label={t("common.toggle_theme")}
      className={`flex h-9 w-9 items-center justify-center rounded-control text-text-secondary transition-colors duration-150 hover:bg-surface-2 hover:text-text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${extraClass}`}
    >
      {theme === "dark" ? <SunMedium size={18} aria-hidden /> : <MoonStar size={18} aria-hidden />}
    </button>
  );

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border-subtle bg-surface-1/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4">
          {/* Brand */}
          <div className="flex items-center gap-6">
            <Link
              href="/app"
              className="flex items-center gap-2 rounded-control focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <span className="text-accent">
                <Logomark size={24} />
              </span>
              <span className="text-sm font-bold text-text-primary">{t("app_name")}</span>
            </Link>
            <nav className="hidden items-center gap-1 md:flex" aria-label={t("a11y.main_nav")}>
              {navLinks()}
            </nav>
          </div>

          {/* Controls */}
          <div className="hidden items-center gap-2 md:flex">
            <LangSwitch />
            {themeToggle()}
            <UserMenu onLogout={() => void logout()} />
          </div>

          {/* Mobile trigger */}
          <Dialog.Root open={mobileOpen} onOpenChange={setMobileOpen}>
            <Dialog.Trigger asChild>
              <button
                type="button"
                aria-label={t("a11y.menu")}
                className="flex h-9 w-9 items-center justify-center rounded-control text-text-secondary transition-colors duration-150 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:hidden"
              >
                <Menu size={20} aria-hidden />
              </button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-900/50" />
              <div className="fixed inset-x-0 top-0 z-50 flex justify-start p-0">
                <Dialog.Content className="h-dvh w-72 max-w-[85vw] rounded-surface border-y-0 border-border-subtle bg-surface-1 shadow-lg outline-none data-[state=open]:animate-in data-[state=closed]:animate-out">
                  <div className="flex h-full flex-col">
                    <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
                      <span className="flex items-center gap-2 text-accent">
                        <Logomark size={22} />
                        <span className="text-sm font-bold text-text-primary">{t("app_name")}</span>
                      </span>
                      <Dialog.Close asChild>
                        <button
                          type="button"
                          aria-label={t("common.close")}
                          className="flex h-9 w-9 items-center justify-center rounded-control text-text-secondary hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                        >
                          <X size={18} aria-hidden />
                        </button>
                      </Dialog.Close>
                    </div>
                    <Dialog.Title className="sr-only">{t("a11y.menu")}</Dialog.Title>
                    <nav
                      className="flex flex-col gap-1 px-3 py-3"
                      aria-label={t("a11y.mobile_nav")}
                    >
                      {navLinks(() => setMobileOpen(false))}
                    </nav>
                    <div className="mt-auto space-y-3 border-t border-border-subtle px-4 py-4">
                      {user && (
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-text-primary">
                            {user.fullname || user.username}
                          </p>
                          <p className="truncate text-xs text-text-muted">@{user.username}</p>
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <LangSwitch />
                        {themeToggle()}
                      </div>
                    </div>
                  </div>
                </Dialog.Content>
              </div>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
