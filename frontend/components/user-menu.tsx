"use client";

/** User identity menu: avatar initials block + Radix DropdownMenu with
 * profile, admin (gated, UI-only — the API enforces), and logout. */

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { LogOut, ShieldCheck, UserRound } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { useLang } from "@/lib/lang-context";

interface UserMenuProps {
  onLogout: () => void;
}

export function UserMenu({ onLogout }: UserMenuProps) {
  const { user } = useAuth();
  const { t } = useLang();

  if (!user) return null;

  const initials = (user.fullname || user.username)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("");

  const itemClass =
    "flex w-full cursor-pointer select-none items-center gap-2 rounded-control px-3 py-2 text-sm text-text-secondary outline-none transition-colors duration-150 data-[highlighted]:bg-surface-2 data-[highlighted]:text-text-primary";

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label={t("profile.title")}
          className="flex h-9 items-center gap-2 rounded-pill border border-border-subtle bg-surface-1 ps-1 pe-3 transition-colors duration-150 hover:border-border-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <span
            aria-hidden
            className="flex h-7 w-7 items-center justify-center rounded-pill bg-accent-soft text-xs font-bold text-accent"
          >
            {initials}
          </span>
          <span className="hidden max-w-32 truncate text-sm text-text-primary sm:block">
            {user.fullname || user.username}
          </span>
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-50 min-w-48 rounded-surface border border-border-subtle bg-surface-1 p-1 shadow-lg"
        >
          <div className="px-3 py-2" dir="auto">
            <p className="truncate text-sm font-semibold text-text-primary">{user.fullname || user.username}</p>
            <p className="truncate text-xs text-text-muted">@{user.username}</p>
          </div>
          <DropdownMenu.Separator className="my-1 h-px bg-border-subtle" />
          <DropdownMenu.Item asChild>
            <a href="/app/profile" className={itemClass}>
              <UserRound size={16} aria-hidden />
              {t("profile.title")}
            </a>
          </DropdownMenu.Item>
          {user.is_admin && (
            <DropdownMenu.Item asChild>
              <a href="/app/admin" className={itemClass}>
                <ShieldCheck size={16} aria-hidden />
                {t("nav.admin_panel")}
              </a>
            </DropdownMenu.Item>
          )}
          <DropdownMenu.Separator className="my-1 h-px bg-border-subtle" />
          <DropdownMenu.Item asChild>
            <button type="button" onClick={onLogout} className={itemClass}>
              <LogOut size={16} aria-hidden />
              {t("nav.logout")}
            </button>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
