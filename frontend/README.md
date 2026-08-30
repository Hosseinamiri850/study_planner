# Study Planner — Frontend (TASK-032)

Next.js 15 (App Router) + TypeScript + Tailwind v4 client for the Flask
backend. The API is the contract (`/api/*` on the Flask app); this frontend
never re-implements business logic.

## Architecture

- **`types/api.ts`** — TypeScript mirrors of the Flask response shapes.
- **`lib/api.ts`** — typed `ApiClient`: one method per endpoint. Browser
  code must use it, never raw `fetch()` against Flask.
- **`lib/auth-context.tsx`** — auth state. Access token lives in memory
  only; the refresh token lives in an httpOnly cookie owned by Next route
  handlers (`app/api/auth/*`). 401 → silent refresh (once) → retry →
  redirect to `/login` when the refresh cookie is dead too. Page reloads
  re-authenticate via silent refresh.
- **`app/api/proxy/[...path]/route.ts`** — same-origin catch-all proxy to
  Flask (forwards the client's `Authorization` header). **No CORS is
  involved anywhere**: the browser only ever talks to the Next origin.
- **`app/api/auth/*`** — login/register/refresh/logout handlers with
  refresh-cookie custody. Logout revokes server-side AND clears the cookie.
- **`middleware.ts`** — coarse redirect gating (cookie presence), UX only;
  the API remains the authorization layer.
- **`lib/i18n/`** — fa/en strings loaded from the backend's canonical
  `locales/*.json` (synced by `scripts/sync-locales.mjs` on predev/prebuild
  — edit the backend files, never the copies). RTL/LTR flips via
  `<html dir>` from `LangProvider`.
- **`lib/theme-context.tsx`** — dark/light; the signed-in preference is
  persisted server-side (`PUT /api/me {theme}`), localStorage only bridges
  the first paint for guests.

## Development

```bash
# terminal 1 — Flask (see repo root README for full setup)
flask --app app run --port 5000

# terminal 2 — Next dev server (http://localhost:3000)
cd frontend
npm install
npm run dev
```

Environment: copy `.env.example` to `.env.local` (defaults work for local
dev; `API_BASE_URL` must point at Flask).

Scripts:

| Script | What |
|---|---|
| `npm run dev` | dev server (Turbopack) |
| `npm run build` | production build |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` |

## Production

`npm run build && npm run start` serves Next on its own port; set
`API_BASE_URL` to the Flask service URL. Deploy Next behind the same
domain as Flask (or a proxy) so cookies stay first-party.

## Pages

| Route | Purpose |
|---|---|
| `/login`, `/register` | auth (Bearer + httpOnly refresh cookie) |
| `/app` | dashboard: stat cards, weekly chart, course progress, task CRUD, session start/stop with live timer |
| `/app/profile` | identity, fullname edit, password change (revokes other sessions) |
| `/app/admin` | majors/courses CRUD (admin only; API enforces 403) |
