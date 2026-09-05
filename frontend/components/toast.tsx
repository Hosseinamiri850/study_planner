"use client";

/** Minimal toast system (Phase 5): success/error feedback that doesn't
 * stack page alerts. Deliberately not a toast library — one message at a
 * time, auto-dismiss, tokens for skin. */

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { CheckCircle2, XCircle } from "lucide-react";

type ToastTone = "success" | "error";

interface ToastState {
  showToast: (tone: ToastTone, message: string) => void;
}

const ToastContext = createContext<ToastState | null>(null);

const TOAST_MS = 4000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ tone: ToastTone; message: string; key: number } | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const keyRef = useRef(0);

  const showToast = useCallback((tone: ToastTone, message: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    keyRef.current += 1;
    setToast({ tone, message, key: keyRef.current });
    timerRef.current = setTimeout(() => setToast(null), TOAST_MS);
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
        {toast && (
          <div
            key={toast.key}
            role="status"
            className={`flex items-center gap-2 rounded-control border px-4 py-2.5 text-sm shadow-lg ${
              toast.tone === "success"
                ? "border-success/30 bg-surface-1 text-success"
                : "border-danger/30 bg-surface-1 text-danger"
            }`}
          >
            {toast.tone === "success" ? <CheckCircle2 size={16} aria-hidden /> : <XCircle size={16} aria-hidden />}
            <span className="text-text-primary">{toast.message}</span>
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastState {
  const state = useContext(ToastContext);
  if (!state) throw new Error("useToast must be used inside <ToastProvider>.");
  return state;
}
