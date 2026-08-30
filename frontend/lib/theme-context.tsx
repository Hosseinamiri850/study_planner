"use client";

/** Theme state. Server-backed: the backend stores the preference
 * (User.theme via PUT /api/me), localStorage mirrors it only so the
 * first paint after login matches before /api/me resolves. Changing the
 * theme persists via the API; guests fall back to localStorage only. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useAuth } from "./auth-context";

type Theme = "dark" | "light";

interface ThemeState {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeState | null>(null);

const STORAGE_KEY = "sp_theme";

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.dataset.theme = theme;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { user, api } = useAuth();
  const [theme, setTheme] = useState<Theme>("dark");

  // Initial resolution: server preference when signed in, else the local
  // mirror. Runs whenever the signed-in user identity changes.
  useEffect(() => {
    if (user) {
      setTheme(user.theme);
      localStorage.setItem(STORAGE_KEY, user.theme);
    } else {
      setTheme((localStorage.getItem(STORAGE_KEY) as Theme | null) ?? "dark");
    }
  }, [user]);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      localStorage.setItem(STORAGE_KEY, next);
      if (user) {
        // Persist to the backend; on failure revert to the server's truth.
        api
          .updateMe({ theme: next })
          .catch(() => {
            setTheme(user.theme);
            localStorage.setItem(STORAGE_KEY, user.theme);
          });
      }
      return next;
    });
  }, [api, user]);

  const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeState {
  const state = useContext(ThemeContext);
  if (!state) throw new Error("useTheme must be used inside <ThemeProvider>.");
  return state;
}
