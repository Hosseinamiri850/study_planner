# 05 — Component Strategy

**STATUS: DRAFT — strategy fixed from audit; skin details follow 03/04.**

Current inventory: `components/ui.tsx` (Button, Input, Textarea, Select, Field, Card, Badge, Alert, Skeleton, EmptyState, Spinner), `app-shell.tsx`, `confirm-dialog.tsx`, `require-auth.tsx`, `stats-cards.tsx` (StatsCards, WeeklyChart), `task-form-dialog.tsx`, `tasks-panel.tsx` (TaskItem).

## Disposition per component

### Preserve as-is (logic intact, restyle only)
- **`require-auth.tsx`** — auth gate. Keep.
- **`app-shell.tsx`** — keep logic (nav gating, controls, mobile menu state); replace chrome (brand mark, avatar block, icon theme toggle, segmented lang control, mobile sheet). Medium refactor, contained.
- **`lib/*` contexts & api client** — untouched. Design work never touches auth/API/i18n plumbing.

### Refactor in place (keep file, restructure internals)
- **`ui.tsx`** — becomes the token-skinned primitive layer. Keep exports/stable names so pages don't churn: Button (add size matrix + icon-button), Input/Textarea/Field (error/hint states), Alert (icon + retry slot), Badge, Spinner. Card gets **surface variants** (`surface` prop: page/panel/inset) instead of one look. EmptyState gets illustration slot + stronger CTA hierarchy.
- **`stats-cards.tsx`** — StatsCards collapses from 4 boxes to a stat strip / hero-metric variant (decision C2). WeeklyChart replaced by token-styled chart (recharts or shadcn chart) with localized weekday axis (G2).

### Replace with shadcn-backed product components
- **`confirm-dialog.tsx`** → **DONE (Phase 2):** Radix `AlertDialog`. Focus trap, scroll lock, Esc, backdrop cancel by construction. Confirm button is a plain Button (not `AlertDialog.Action`) so the parent controls close timing — dialog stays up while loading / on failed delete.
- **`task-form-dialog.tsx`** → **DONE (Phase 2):** Radix `Dialog`; form logic + validation untouched; first-field autofocus via Radix.
- Native `<select>`s → shadcn Select (desktop) pending Q10; language switcher → segmented control component (new, tiny).

### New product-specific components (only where reuse is real)
- **`RunningSessionBar`** — **DONE (Phase 4):** docked hero timer, display-face tabular clock, one stop control. Dashboard owns all session state.
- **`CourseProgressList`** — **DONE (Phase 4):** zero-activity filtering, activity sort, cap + show-all (fixes C3).
- **`UserMenu`** — **DONE (Phase 3):** avatar + dropdown (identity, profile, admin link, logout).
- **`StatsStrip` + recharts `WeeklyChart`** — **DONE (Phase 4):** replaced 4-box StatsCards + div-chart.
- **`LangSwitch`** — **DONE (Phase 3):** segmented fa/EN control.
- **`Logomark`** — **DONE (Phase 3):** brand SVG.
- **`403 page`** (`app/forbidden` or route segment) — missing today (F3), planned Phase 6.

### Delete
- Nothing deleted outright; `ui.tsx` pieces that get superseded (e.g. native select wrapper if replaced) are removed once call sites migrate — no parallel shims, no backwards-compat aliases.

## Anti-abstraction rules

- No `ComponentProvider`, no theming indirection beyond CSS tokens, no wrapper components that only forward className.
- A new component exists only if ≥2 real call sites or it encapsulates state (dialogs, timer).
- Pages may compose primitives directly; we don't force section components per page.

## Migration safety

All call-site changes are in-page; no API/auth/i18n signature changes. Each phase in 07-migration-plan.md lists exact files; `pytest` + `npm run typecheck` + `npm run lint` gate every phase.
