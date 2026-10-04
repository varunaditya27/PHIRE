# Frontend Handoff: Architecture, Implemented UI, and Integration Guide

**Audience**: Shashwati (`frontend/`, `evaluation/`) & Frontend Maintainers.  
**As of**: 2026-10-05 (reviewed end to end in real Chrome against the Docker stack).  
**Status**: The Next.js UI is built and verified with Dashboard, Chat, Document Ingestion, and Search views, live SSE progress, a mobile layout, and a missing-document-date prompt. This document maps the architecture, live routes, data flows, and what is still open.

---

## 1. Quick Start & Local Development

### Running the Stack
Easiest: `bash scripts/run.sh` starts everything in Docker, including this frontend (`http://localhost:3000`, or your `FRONTEND_PORT`; GPU or CPU variant chosen automatically — see `docs/BACKEND_HANDOFF.md` §8 and `docs/CPU_SETUP.md`). For frontend development, run the backend services (PostgreSQL, Ollama, Neo4j, FastAPI) and then the dev server:
```bash
# Terminal 1: Backend
bash scripts/run_backend.sh

# Terminal 2: Frontend
cd frontend
npm install
npm run dev   # Runs on http://localhost:3000 (use `npx next dev -p 3001` if 3000 is taken; add that origin to the backend's CORS_ORIGINS)
```

### Environment Configuration
- Default `NEXT_PUBLIC_API_URL` is `http://localhost:8000` (an **empty** value means same-origin, for use behind the nginx proxy profile).
- Override by placing `NEXT_PUBLIC_API_URL=...` in `frontend/.env.local`. In Docker it is a **build** argument (Next.js inlines it into the bundle), so changing it needs a rebuild.
- Backend CORS (`CORS_ORIGINS` in `backend/.env`) defaults to `["http://localhost:3000"]`; the Docker setup derives it from `FRONTEND_PORT`.

---

## 2. Implemented Pages & UI Inventory

| Route | File Path | Description & Features |
|---|---|---|
| **`/` (Dashboard)** | [`frontend/app/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/page.tsx) | **Patient Overview & Health Timeline**: Fetches `GET /api/timeline` and `GET /api/observations`. Renders one Recharts chart **per unit** (`components/timeline-chart.tsx`: mg/dL, mmHg, %, … so unlike scales never share an axis; 8-colour palette legible in light and dark; series with no numeric readings skipped; blood pressure charted as Systolic and Diastolic) and a **Latest Readings** feed (latest per metric, newest first; conditions/medications show their status; units are not repeated — `lib/readings.ts`). A banner links to the Documents page when any document needs a date. |
| **`/chat` (Medical Chat)** | [`frontend/app/chat/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/chat/page.tsx) | **Evidence-Attributed Assistant**: Multi-turn chat interface calling `POST /api/chat/stream` (SSE): while the backend works, a live step checklist (`components/progress-steps.tsx`) shows each stage with a per-step elapsed timer, replacing the old static spinner. Features expandable per-claim audit trails with NLI status badges (`SUPPORTED`, `DERIVED`, `CONFLICTING`, `UNSUPPORTED`), confidence percentages, and source file citations. |
| **`/documents` (Ingestion)** | [`frontend/app/documents/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/documents/page.tsx) | **Document Uploader**: Drag-and-drop file uploader (PDF, PNG, JPEG) up to 25MB calling `POST /api/documents/upload`. Live ingestion progress over SSE from `GET /api/documents/{id}/events` (stage checklist on each card: queued → loading vision model → reading document → indexing → saving to timeline → done/failed); the old 2.5s polling is gone. On stream end the page re-reads the final row via `GET /api/documents/{id}`. A processed document flagged `needs_date` (no date could be extracted) shows an inline date prompt (`components/date-needed-prompt.tsx`) that calls `PUT /api/documents/{id}/date`; the backend then rebuilds that document's facts and search chunks at the user's date. |
| **`/search` (Explorer)** | [`frontend/app/search/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/search/page.tsx) | **Evidence & Claim Explorer**: Tab 1 executes hybrid search via `GET /api/search/evidence`. Tab 2 allows direct NLI claim verification via `POST /api/evidence/verify`. |

---

## 3. Design System & Tokens

Defined in [`frontend/app/globals.css`](file:///home/varun/Projects/PHIRE/frontend/app/globals.css) and [`DESIGN.md`](file:///home/varun/Projects/PHIRE/DESIGN.md):
- **Color Palette**:
  - `Canvas`: `--background` (`#FAF8F5` light / `#18181B` dark)
  - `Surface`: `--card` (`#FFFFFF` light / `#27272A` dark)
  - `Accent / Ochre`: `--primary` (`#96742A` light / `#D4AF37` dark)
  - `Evidence / Slate`: `var(--evidence)` (`#3B5B6D` light / `#6895AC` dark)
  - `Positive / Oxide Green`: `var(--positive)` (`#2B6E4E` light / `#4ADE80` dark)
  - `Danger / Oxide Red`: `var(--danger)` (`#8C3F2B` light / `#F87171` dark)
- **Typography Pairings**:
  - Body: `IBM Plex Sans` (`var(--font-sans)`)
  - Headings / Editorial: `Newsreader` (`var(--font-editorial)`)
  - Numerical metrics / IDs / Spans: `IBM Plex Mono` (`var(--font-mono)`)

---

**Cross-cutting UI (added `[0.8.1]`):** below the `md` breakpoint the sidebar becomes a compact top bar (`MobileNav` in `components/sidebar.tsx`) and page padding shrinks, so the app is usable at 390px; a wellness/not-a-medical-device disclaimer is shown in the sidebar and under the chat input; the documents card badge follows the live SSE stream (it used to read "Uploaded" for the whole run); search and verifier results link to their public source URL.

---

## 4. API Client & Data Models (`frontend/lib/api.ts`)

The frontend communicates with the backend exclusively via typed wrappers in [`frontend/lib/api.ts`](file:///home/varun/Projects/PHIRE/frontend/lib/api.ts):
- `api.health.check()`: Calls `POST /api/health`
- `api.health.ping()`: Calls `GET /api/ping`
- `api.chat.send(message)`: Calls `POST /api/chat` (non-streaming; still available)
- `api.documents.upload(file)`: Streams `multipart/form-data` to `POST /api/documents/upload`
- `api.documents.remove(id)`: Calls `DELETE /api/documents/{id}` (documents page trash button, confirm dialog; throws the server's `detail` on 409/404)
- `api.documents.list()`: Calls `GET /api/documents` (documents page loads from the backend)
- `api.chat.history()`: Calls `GET /api/chat/messages` (chat page rehydrates on mount)
- `api.documents.setDate(id, 'YYYY-MM-DD')`: Calls `PUT /api/documents/{id}/date` (supplies a missing clinical date; returns the updated document)
- `api.documents.get(id)`: Calls `GET /api/documents/{id}` (final status after a stream ends)
- `api.documents.watch(id, onProgress, signal?)`: SSE stream from `GET /api/documents/{id}/events`; resolves when the server closes it
- `api.chat.stream(message, onProgress)`: SSE from `POST /api/chat/stream`; calls `onProgress` per stage and resolves with the final `ChatResponse` (rejects on an `error` event)
- `api.observations.list(params)`: Calls `GET /api/observations`
- `api.timeline.get()`: Calls `GET /api/timeline`
- `api.evidence.search(query, top_k)`: Calls `GET /api/search/evidence`
- `api.evidence.verify(claim)`: Calls `POST /api/evidence/verify`
- `api.claims.extract(text)`: Calls `POST /api/claims/extract`

SSE is read with `frontend/lib/sse.ts`'s `readSSE()` (fetch + stream reader, so it works for POST; `EventSource` is GET-only). `ProgressEvent` (`{stage, message}`) is exported from `api.ts`.

---

## 5. Active Frontend Work Items & Gaps

1. ~~**Fix `EvidenceCitation.score` in Search**~~ — **done in `[0.7.1]` (backend).** Original note:
   Backend `chunk_to_citation()` leaves `score` as `None`, causing `frontend/app/search/page.tsx` to display `0.0%`. Pass score through in backend service.
2. ~~**Remove `localStorage` Workaround for Documents**~~ — **done in `[0.7.2]`** (page uses `GET /api/documents`). Original note:
   Currently, `frontend/app/documents/page.tsx` caches document IDs in browser `localStorage`. Once backend exposes `GET /api/documents`, switch to fetching the full document list directly on component mount.
3. ~~**Add Chat History Rehydration**~~ — **done in `[0.7.2]`** (`api.chat.history()` on mount). Original note:
   Implement a chat message list fetch on mount in `frontend/app/chat/page.tsx` once backend exposes `GET /api/chat/messages`.
4. ~~**Remove Redundant Ingestion Call**~~ — **done 2026-10-04.** The documents page no longer calls `api.documents.process` after upload (it would also have reset the SSE progress history mid-run); it just watches the stream.
5. ~~**Type Alignment**~~ — **done** (`Claim.source_span` is `[number, number] | null`, `ObservationRead.value`/`observed_date` are nullable, `Claim.source_filenames`, `DocumentRead.document_date`/`needs_date`).
6. ~~**Observation Status Badges**~~ — **done**: conditions and medications show their status as the card's headline value on the dashboard.

**Still open** (details in `docs/BACKLOG.md` §1): no automated frontend tests (a Playwright smoke test is the natural next step — the `[0.8.1]` review drove every page with `playwright-core` + system Chrome), chat has no "clear conversation" or timestamps, navigating away mid-chat does not abort the stream, the dashboard has no date-range filter, no accessibility pass yet, and `frontend/lib/api.ts` still has a few `any` types (existing ESLint errors).
