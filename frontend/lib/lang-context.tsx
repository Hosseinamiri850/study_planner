"use client";

/** Language preference context. Persisted in localStorage (UI concern only
 * — the backend session language is independent). `dir` flips at the root
 * layout via a script-free effect; first paint uses the fa default to
 * avoid a flash, matching the Jinja app's default. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { dirOf, resolveLang, t, type Lang } from "./i18n";

interface LangState {
  lang: Lang;
  dir: "rtl" | "ltr";
  t: (key: string, params?: Record<string, string | number>) => string;
  setLang: (lang: Lang) => void;
}

const LangContext = createContext<LangState | null>(null);

const STORAGE_KEY = "sp_lang";

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("fa");

  useEffect(() => {
    setLangState(resolveLang(localStorage.getItem(STORAGE_KEY)));
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dirOf(lang);
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const value = useMemo<LangState>(
    () => ({
      lang,
      dir: dirOf(lang),
      t: (key, params) => t(lang, key, params),
      setLang,
    }),
    [lang, setLang],
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): LangState {
  const state = useContext(LangContext);
  if (!state) throw new Error("useLang must be used inside <LangProvider>.");
  return state;
}
