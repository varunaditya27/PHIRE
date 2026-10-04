# PHIRE `frontend/`

**Owned by Shashwati (Frontend & Evaluation).** The Next.js 16 (App Router, React 19, TypeScript, Tailwind) UI for
PHIRE: a patient dashboard, an evidence-attributed chat, document upload/ingestion, and an evidence & claim explorer.
It talks only to PHIRE's own backend (`NEXT_PUBLIC_API_URL`, default `http://localhost:8000`) — nothing leaves the
machine. See the [root README](../README.md) for the whole system and
[docs/FRONTEND_HANDOFF.md](../docs/FRONTEND_HANDOFF.md) for the architecture, page inventory and open items.

## Pages

| Route | What it does |
|---|---|
| `/` | Dashboard: one chart per unit (mg/dL, mmHg, %, …), latest reading per metric, a banner when a document needs a date |
| `/chat` | Chat with a live step-by-step progress panel (SSE), a per-claim audit trail (status, confidence, every source file), history that survives a reload |
| `/documents` | Upload (PDF/PNG/JPEG), live ingestion progress (SSE), delete, and an inline date prompt for a document where no date could be extracted |
| `/search` | Hybrid evidence search with relevance scores, and a direct claim verifier |

Layout: `app/` pages, `components/` (sidebar + mobile nav, progress steps, timeline chart, date prompt),
`lib/api.ts` (typed API client), `lib/sse.ts` (fetch-based SSE reader), `lib/readings.ts` (unit-aware reading helpers).
The UI works at phone width (the sidebar becomes a top bar) and in light and dark mode.

## Run it

Everything together, in Docker (GPU or CPU variant chosen automatically): `bash scripts/run.sh` from the repo root.

For frontend development (backend already running on :8000):

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000   (npx next dev -p 3001 if 3000 is taken — add that origin to the backend's CORS_ORIGINS)
npm run build && npm start     # production build
npx tsc --noEmit     # type check
npm run lint         # ESLint (some pre-existing errors are listed in docs/BACKLOG.md)
```

## Configuration

`NEXT_PUBLIC_API_URL` — the backend's base URL. Next.js inlines it into the bundle at **build** time (so in Docker it
is a build argument and changing it needs a rebuild); an empty value means same-origin, for use behind the nginx
proxy profile. Put it in `frontend/.env.local` for local development.

## Notes for contributors

- This is Next.js 16: APIs and conventions differ from older versions — see `AGENTS.md` and
  `node_modules/next/dist/docs/` before writing code.
- Server-Sent Events: `lib/sse.ts` reads a `fetch` stream, so it also works for POST (chat). Stage lists and frame
  formats are in [docs/API_REFERENCE.md](../docs/API_REFERENCE.md).
- There are no automated frontend tests yet; the UI was verified by driving every page in real Chrome
  (see `docs/BACKLOG.md` §1). Adding a committed smoke test is the suggested next step.
- Safety: the UI shows a wellness / not-a-medical-device disclaimer (sidebar, and under the chat input). Keep it.
