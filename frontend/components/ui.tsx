"use client";

/** Shared UI primitives, skinned on the design-token layer (globals.css).
 * Docs: docs/redesign/04-design-system.md. Tailwind v4 with logical
 * properties (ps-/pe-/ms-/me-) so RTL mirrors for free; dark mode via the
 * `dark` class strategy. Export names are stable — pages keep compiling. */

import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

// --- Buttons ---

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "icon";

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-accent-fg hover:bg-accent-hover focus-visible:outline-accent shadow-none",
  secondary:
    "bg-surface-2 text-text-primary hover:border-border-strong border border-border-subtle focus-visible:outline-accent",
  danger:
    "bg-danger-strong text-white hover:opacity-90 focus-visible:outline-danger",
  ghost:
    "bg-transparent text-text-secondary hover:bg-surface-2 hover:text-text-primary focus-visible:outline-accent",
};

const buttonSizes: Record<ButtonSize, string> = {
  sm: "h-8 gap-1.5 px-3 text-xs",
  md: "h-9 gap-2 px-4 text-sm",
  icon: "h-9 w-9 p-0",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, disabled, className = "", children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`inline-flex shrink-0 items-center justify-center rounded-control font-medium transition-colors duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${buttonVariants[variant]} ${buttonSizes[size]} ${className}`}
      {...rest}
    >
      {loading && (
        <span aria-hidden className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
});

// --- Inputs ---

const fieldBase =
  "w-full rounded-control border border-border-strong bg-surface-1 px-3 text-sm text-text-primary placeholder:text-text-muted transition-colors duration-150 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-50";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className = "", ...rest },
  ref,
) {
  return <input ref={ref} className={`h-9 ${fieldBase} ${className}`} {...rest} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea(
  { className = "", ...rest },
  ref,
) {
  return <textarea ref={ref} className={`py-2 ${fieldBase} ${className}`} {...rest} />;
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className = "", children, ...rest },
  ref,
) {
  return (
    <select ref={ref} className={`h-9 ${fieldBase} ${className}`} {...rest}>
      {children}
    </select>
  );
});

export function Field({
  label,
  error,
  htmlFor,
  children,
  hint,
}: {
  label: string;
  error?: string | null;
  htmlFor?: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-text-primary">
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-text-muted">{hint}</p>}
      {error && (
        <p role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

// --- Cards / surfaces ---

/** Surface levels (04 §3): `panel` = raised content block, `inset` = nested
 * or de-emphasized block. Borders stay hairline-subtle; elevation comes
 * from surface color, not shadow stacking. */
export function Card({
  children,
  className = "",
  variant = "panel",
}: {
  children: ReactNode;
  className?: string;
  variant?: "panel" | "inset";
}) {
  const variantClass =
    variant === "inset"
      ? "bg-surface-2 border-border-subtle"
      : "bg-surface-1 border-border-subtle";
  return <div className={`rounded-surface border ${variantClass} ${className}`}>{children}</div>;
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "success" | "warning" | "danger" }) {
  const tones = {
    default: "bg-surface-2 text-text-secondary",
    success: "bg-success/10 text-success",
    warning: "bg-warning/10 text-warning",
    danger: "bg-danger/10 text-danger",
  } as const;
  return <span className={`inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

export function Alert({ tone = "error", children }: { tone?: "error" | "success" | "info"; children: ReactNode }) {
  const tones = {
    error: "border-danger/30 bg-danger/10 text-danger",
    success: "border-success/30 bg-success/10 text-success",
    info: "border-accent/30 bg-accent/10 text-accent",
  } as const;
  return (
    <div role="status" className={`flex items-start gap-2 rounded-control border px-3 py-2 text-sm ${tones[tone]}`}>
      {children}
    </div>
  );
}

// --- Loading / empty ---

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-control bg-surface-2 ${className}`} />;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-surface border border-dashed border-border-strong px-6 py-12 text-center">
      <p className="text-sm font-semibold text-text-primary">{title}</p>
      <p className="max-w-sm text-sm text-text-muted">{description}</p>
      {action}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-8 text-sm text-text-muted">
      <span aria-hidden className="h-5 w-5 animate-spin rounded-full border-2 border-border-strong border-t-accent" />
      {label}
    </div>
  );
}
