# 06 — Page Redesign Plan

**STATUS: DRAFT — hierarchy decisions marked [Q] depend on interview answers; rest is fixed from audit.**

## Page inventory (SPA, 8 routes)

| Route | File | User importance | Redesign priority |
|---|---|---|---|
| `/login` | app/login/page.tsx | every visitor, first touch | 2 |
| `/register` | app/register/page.tsx | first-run | 3 |
| `/app` (dashboard) | app/app/page.tsx | **the product** | **1** |
| `/app/profile` | app/app/profile/page.tsx | occasional | 5 |
| `/app/admin` | app/app/admin/page.tsx | admins only | 4 |
| `/` | app/page.tsx | redirect only | — (no visual work) |
| `not-found` / 403 | missing | error paths | 6 |

## 1. `/app` — Dashboard (student)

- **Purpose:** see where I stand today; start/stop study time; manage today's tasks.
- **Primary goal:** start studying (timer) or log progress — everything else supports that.
- **Hierarchy [Q9-dependent]:** greeting (small, human) → dominant zone: running session / weekly hero metric → task list (workspace) → compact stat strip → course progress (filtered) / chart (secondary column).
- **Components:** RunningSessionBar (new), TaskItem (skinned), StatsStrip (refactor), CourseProgressList (new), chart (replaced), dialogs (Radix).
- **Interactions:** task toggle stays inline; session start/stop stays per-task; timer docks instead of alert-chip.
- **Responsive:** mobile = single column in priority order (timer → tasks → stats → courses); chart below fold.
- **Empty:** first-run onboarding moment (E1): one CTA + course suggestion, not dashed box.
- **Loading:** skeleton shapes match final layout (no generic blocks).
- **Error:** per-zone error with retry; timer state never blocked by stats errors (already true — preserve).

## 2. `/login`

- **Purpose:** frictionless entry; establish brand at first touch.
- **Hierarchy:** brand moment (wordmark/logomark, product line) → form card → register link. Currently a bare card floating in gray.
- **Layout:** centered narrow card; optional split-brand treatment [Q1/Q2-dependent].
- **States:** submitting (button), invalid (inline), server error (alert), rate-limit message (i18n — backend English string today).
- **RTL/LTR:** card is direction-neutral; brand block flips.

## 3. `/register`

- Same system as login. Password hints (`validation.password_hint`) styled as hint text; field-level errors remain inline. Success → auto-login (existing flow preserved).

## 4. `/app/admin`

- **Purpose:** majors/courses CRUD.
- **Problems today:** two tall cards of forms+lists stacked, success/error alerts stacked at top disconnected from actions, protected-major rule only visible as disabled button.
- **Hierarchy:** page title + zone marker (admin surface treatment) → Majors panel → Courses panel (grouped by major, not flatMap list) → toasts for action feedback instead of top alerts.
- **Interactions:** create forms keep inline placement; delete confirmations via AlertDialog (existing logic).
- **Empty:** no majors → seed hint; major with no courses → inline empty note.

## 5. `/app/profile`

- **Purpose:** identity + security self-service.
- **Problems today:** three identical cards; identity card shows username twice (label vs value); success alerts appear above forms.
- **Hierarchy:** identity header (avatar block, member since) → fullname form → password form (note about token revocation as info-callout). Toasts for save feedback.

## 6. Error routes

- `not-found.tsx` + `forbidden` route: branded, in both languages, escape link. Currently nonexistent in SPA.

## Cross-page rules

- One page-hero pattern (title + context), never giant hero sections.
- All lists: same row anatomy (primary text / meta / actions) across tasks, courses, majors.
- All forms: same Field anatomy (label / control / hint-or-error) — already good, formalize in primitives.
- Success feedback: toasts (page-level alerts reserved for blocking errors).
