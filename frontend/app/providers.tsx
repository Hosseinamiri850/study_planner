"use client";

import type { ReactNode } from "react";

import { AuthProvider } from "@/lib/auth-context";
import { LangProvider } from "@/lib/lang-context";
import { ThemeProvider } from "@/lib/theme-context";

/** Client provider stack: language (dir/i18n) -> auth -> theme (theme
 * reads the signed-in user). */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <LangProvider>
      <AuthProvider>
        <ThemeProvider>{children}</ThemeProvider>
      </AuthProvider>
    </LangProvider>
  );
}
