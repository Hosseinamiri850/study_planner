"use client";

import type { ReactNode } from "react";

import { AuthProvider } from "@/lib/auth-context";
import { LangProvider } from "@/lib/lang-context";
import { ThemeProvider } from "@/lib/theme-context";
import { ToastProvider } from "@/components/toast";

/** Client provider stack: language (dir/i18n) -> auth -> theme (theme
 * reads the signed-in user) -> toast. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <LangProvider>
      <AuthProvider>
        <ThemeProvider>
          <ToastProvider>{children}</ToastProvider>
        </ThemeProvider>
      </AuthProvider>
    </LangProvider>
  );
}
