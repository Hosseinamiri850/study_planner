"use client";

/** Modal confirmation dialog for destructive actions, on Radix
 * AlertDialog: focus trap, scroll lock, Esc to cancel, accessible by
 * construction. Visuals from the token layer. */

import * as AlertDialog from "@radix-ui/react-alert-dialog";

import { useLang } from "@/lib/lang-context";
import { Button } from "./ui";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  danger = true,
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useLang();

  return (
    <AlertDialog.Root open={open} onOpenChange={(next: boolean) => { if (!next) onCancel(); }}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-50 bg-slate-900/50 data-[state=open]:animate-in data-[state=closed]:animate-out" />
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <AlertDialog.Content
            className="w-full max-w-sm rounded-surface border border-border-subtle bg-surface-1 p-5 shadow-lg data-[state=open]:animate-in data-[state=closed]:animate-out"
            aria-describedby={description ? "confirm-description" : undefined}
          >
            <AlertDialog.Title className="text-base font-semibold text-text-primary">
              {title}
            </AlertDialog.Title>
            {description && (
              <AlertDialog.Description id="confirm-description" className="mt-1 text-sm text-text-muted">
                {description}
              </AlertDialog.Description>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <AlertDialog.Cancel asChild>
                <Button variant="secondary" disabled={loading}>
                  {cancelLabel ?? t("common.cancel")}
                </Button>
              </AlertDialog.Cancel>
              {/* Plain button, not AlertDialog.Action: the parent controls
                  close timing so the dialog can stay up while loading and
                  on a failed delete. */}
              <Button variant={danger ? "danger" : "primary"} loading={loading} onClick={onConfirm}>
                {confirmLabel ?? t("common.confirm")}
              </Button>
            </div>
          </AlertDialog.Content>
        </div>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
