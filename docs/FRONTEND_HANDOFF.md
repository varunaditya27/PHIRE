# Frontend Handoff: Architecture, Implemented UI, and Integration Guide

**Audience**: Shashwati (`frontend/`, `evaluation/`) & Frontend Maintainers.  
**As of**: 2026-09-03 (Frontend V1 Implemented on `main`).  
**Status**: The Next.js UI is fully built with Dashboard, Chat, Document Ingestion, and Search views. This document maps the architecture, live routes, data flows, and active backlog items.

---

## 1. Quick Start & Local Development

### Running the Stack
Ensure the backend services (PostgreSQL, Ollama, Neo4j, FastAPI) are running at `http://localhost:8000`:
```bash
# Terminal 1: Backend
bash scripts/run_backend.sh

# Terminal 2: Frontend
cd frontend
npm install
npm run dev   # Runs on http://localhost:3000
```

### Environment Configuration
- Default `NEXT_PUBLIC_API_URL` is `http://localhost:8000`.
- Override by placing `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.
- Backend CORS (`CORS_ORIGINS` in `backend/.env`) defaults to `["http://localhost:3000"]`.

---

## 2. Implemented Pages & UI Inventory

| Route | File Path | Description & Features |
|---|---|---|
| **`/` (Dashboard)** | [`frontend/app/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/page.tsx) | **Patient Overview & Health Timeline**: Fetches `GET /api/timeline` and `GET /api/observations`. Renders multi-series Recharts line graphs for numeric lab metrics and a recent observations feed. |
| **`/chat` (Medical Chat)** | [`frontend/app/chat/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/chat/page.tsx) | **Evidence-Attributed Assistant**: Multi-turn chat interface calling `POST /api/chat`. Features expandable per-claim audit trails with NLI status badges (`SUPPORTED`, `DERIVED`, `CONFLICTING`, `UNSUPPORTED`), confidence percentages, and source file citations. |
| **`/documents` (Ingestion)** | [`frontend/app/documents/page.tsx`](file:///home/varun/Projects/PHIRE/frontend/app/documents/page.tsx) | **Document Uploader**: Drag-and-drop file uploader (PDF, PNG, JPEG) up to 25MB calling `POST /api/documents/upload`. Live polling against `GET /api/documents/{id}` for `processing`, `processed`, or `failed` status. |
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

## 4. API Client & Data Models (`frontend/lib/api.ts`)

The frontend communicates with the backend exclusively via typed wrappers in [`frontend/lib/api.ts`](file:///home/varun/Projects/PHIRE/frontend/lib/api.ts):
- `api.health.check()`: Calls `POST /api/health`
- `api.health.ping()`: Calls `GET /api/ping`
- `api.chat.send(message)`: Calls `POST /api/chat`
- `api.documents.upload(file)`: Streams `multipart/form-data` to `POST /api/documents/upload`
- `api.documents.get(id)`: Polls `GET /api/documents/{id}`
- `api.observations.list(params)`: Calls `GET /api/observations`
- `api.timeline.get()`: Calls `GET /api/timeline`
- `api.evidence.search(query, top_k)`: Calls `GET /api/search/evidence`
- `api.evidence.verify(claim)`: Calls `POST /api/evidence/verify`
- `api.claims.extract(text)`: Calls `POST /api/claims/extract`

---

## 5. Active Frontend Work Items & Gaps

1. **Fix `EvidenceCitation.score` in Search**:
   Backend `chunk_to_citation()` leaves `score` as `None`, causing `frontend/app/search/page.tsx` to display `0.0%`. Pass score through in backend service.
2. **Remove `localStorage` Workaround for Documents**:
   Currently, `frontend/app/documents/page.tsx` caches document IDs in browser `localStorage`. Once backend exposes `GET /api/documents`, switch to fetching the full document list directly on component mount.
3. **Add Chat History Rehydration**:
   Implement a chat message list fetch on mount in `frontend/app/chat/page.tsx` once backend exposes `GET /api/chat/messages`.
4. **Remove Redundant Ingestion Call**:
   Remove `api.documents.process(res.id)` in `frontend/app/documents/page.tsx:L98` since backend `/upload` already enqueues background processing automatically.
5. **Type Alignment**:
   Update `Claim.source_span` to `[number, number] | null` and `ObservationRead.value` to `string | null` in `frontend/lib/api.ts`.
6. **Observation Status Badges**:
   Display medication and condition statuses (e.g. `"active"`, `"continued"`) as pill badges in `frontend/app/page.tsx`.
