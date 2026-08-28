# Frontend Handoff: what's built in `backend/` + `ml/`, and what you need to know

**Audience**: Shashwati (`frontend/`, `evaluation/`). This is a snapshot of
`backend/` + `ml/` as of 2026-08-28 (`origin/backend` branch) — what's
live, how to call it, what infrastructure you need running, and what's
still rough. Written so you can start `frontend/` without reading
`backend/app/` or `ml/` first. For the exact request/response shape of
every endpoint, see **[docs/API_REFERENCE.md](API_REFERENCE.md)** — this
doc is the narrative map, that one is the contract.

**Status of this doc**: accurate as of the commits on `origin/backend`
through the review/fix pass described in `CHANGELOG.md`'s `[0.4.0]`. If
`backend/`/`ml/` change after this, treat this as a starting map, not a
live contract — check `docs/API_REFERENCE.md` or the actual router code
for anything you're about to depend on precisely.

**No frontend code exists yet** — `frontend/` is still the unmodified
`create-next-app` scaffold (Next.js 16, React 19, Tailwind 4). Everything
below is what you're building against from a clean slate, not a migration.

---

## 1. Get the stack running

You need Postgres + Ollama + Neo4j + backend reachable at
`http://localhost:8000` before frontend can do anything real.

**Fastest path (Docker, full stack):**
```bash
cp .env.example .env && cp backend/.env.example backend/.env
scripts/run.sh   # docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml exec ollama ollama pull medgemma:4b
docker compose -f docker/docker-compose.yml exec ollama ollama pull qwen3.5:9b
curl -X POST http://localhost:8000/api/health   # confirm all four deps are true
```
See [backend/README.md](../backend/README.md) and
[docs/BACKEND_HANDOFF.md §8](BACKEND_HANDOFF.md) for the non-Docker path
and platform caveats (host networking is Linux-native; Docker Desktop
Mac/Windows needs a beta opt-in).

**Frontend dev server**, once the backend's up:
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local   # doesn't exist yet -- create it
npm run dev   # http://localhost:3000
```
Backend's CORS (`CORS_ORIGINS` in `backend/.env`) already defaults to
`http://localhost:3000`, so a default `npm run dev` should just work
against a locally running backend with no config changes on either side.

**No seed/demo patient data ships yet.** To have anything to render, either
upload a real PDF/PNG/JPEG lab report through `POST /api/documents/upload`
yourself, or ask Varun/Anika for a synthetic one — `docs/BACKEND_HANDOFF.md
§7` used a PyMuPDF-generated fixture for testing, not committed to the
repo.

---

## 2. What's actually there to build against

All 8 routers are wired to real implementations (not mocks/stubs), and
have been live-tested end-to-end against real Postgres/Neo4j/Chroma/Ollama
(`docs/BACKEND_HANDOFF.md §7`) — full detail in
[docs/API_REFERENCE.md](API_REFERENCE.md):

| Feature | Endpoint(s) | Notes |
|---|---|---|
| Chat (evidence-attributed Q&A) | `POST /api/chat` | Blocking, no streaming — multi-second latency is normal |
| Document upload/ingestion | `POST /api/documents/upload`, `POST /api/documents/{id}/process`, `GET /api/documents/{id}` | Async — poll for status |
| Structured patient data | `GET /api/observations`, `GET /api/timeline` | Backed by the Neo4j graph, not Postgres |
| Evidence search/verify | `GET /api/search/evidence`, `POST /api/evidence/retrieve`, `POST /api/evidence/verify` | |
| Claim extraction (standalone) | `POST /api/claims/extract` | Rarely called directly — `/api/chat` does this internally |
| Health check | `POST /api/health` | Good for a system-status indicator |
| Recommendations | `GET /api/recommendations/fitness`, `/nutrition` | **Not usable yet — always 501**, see below |

### What's genuinely not ready
- **Recommendations (fitness + nutrition) are stubs.** Both return `501`
  unconditionally — `ml/recommendations/` has no `recommend()` function
  yet. Don't build UI that expects real data here; a "coming soon" state
  or feature-flagged-off is the honest option today.
- **No pytest suite** on `backend/` or a frontend test harness yet —
  verification so far is live manual integration testing.

---

## 3. Things that will bite you if you don't know them going in

- **No streaming.** `/api/chat` returns one JSON blob once the whole
  pipeline (retrieve → generate → extract claims → verify each → score)
  finishes — expect several real seconds, not a fast API call. Build a
  loading state, not a token-by-token typing effect (there's nothing to
  stream from).
- **IDs are inconsistent by design.** `Document`/`Claim`/`ChatMessage` ids
  are real UUIDs (Postgres rows). `Observation` ids and evidence-citation
  ids (`evidence_passage_id`, `document_id` on those two) are
  content-derived **strings** from `ml/`'s Neo4j graph / Chroma store —
  don't assume every `id` field is UUID-shaped, and don't try to look one
  up as a Postgres row.
- **`ChatResponse.citations` is declared but always empty today.** Use
  `claims[].source_filename` / `source_url` / `source_span` instead for
  citation rendering — see `docs/API_REFERENCE.md`'s Chat section.
- **The chat answer is pre-filtered.** `answer` only reflects claims that
  passed verification above the confidence threshold; if nothing did,
  you get a fixed abstention message. Still render `claims` even then —
  it's the audit trail of what was checked (including rejected claims),
  which is PHIRE's whole evidence-attribution pitch. Don't hide it.
- **Document processing has no push notification.** After upload, poll
  `GET /api/documents/{id}` yourself; there's no websocket/SSE for
  status changes.
- **A chat request and a document upload can make each other visibly
  slower**, not error. The backend serializes GPU-heavy work (chat
  generation vs. document ingestion) server-side to avoid an out-of-memory
  crash on the dev GPU — if you send a chat message while a document is
  mid-ingestion, it'll just wait its turn. Don't interpret a slow response
  in that situation as a bug.
- **Single patient, no auth, no `patient_id` anywhere.** PHIRE runs one
  instance per person by design — there's no login flow or per-user
  scoping to build.

---

## 4. Who to ask

- **API contract questions, endpoint bugs**: Anika (`backend/`) —
  `docs/BACKEND_HANDOFF.md` has the full integration history if you want
  the "why" behind a shape before asking.
- **Answer quality, claim verification behavior, recommendation
  timeline**: Varun (`ml/`) — `ml/README.md` covers what's implemented
  there.
- Cross-cutting API contract changes (anything that would change a
  response shape you're already relying on) should be a heads-up to
  whoever owns that endpoint before it ships, not a silent change — see
  the root `CLAUDE.md`/`REPO_STRUCTURE.md`'s ownership table.
