# Integration Handoff (`integration/ocr-test`)

## Current Integration State
The `integration/ocr-test` branch is a temporary integration and testing branch combining:
- PR #5 OCR/LIFT changes
- Existing `ml-remaining-work` WIP
- Local E2E/testing work

This branch is being used to validate compatibility before any formal merge of PR #5. 

**Explicit Notes:**
- WIP changes remain intentionally uncommitted in the Git index.
- Do not reset, clean, discard, or otherwise remove the WIP.
- Do not assume that successful startup means the OCR/LIFT → RAG → QA pipeline has been fully validated.

## Verified So Far
- Docker Compose defines:
  - postgres
  - neo4j
  - ollama
  - backend
  - frontend
- Docker infrastructure can be started when Docker Desktop is running.
- Frontend and backend can communicate once backend startup succeeds.
- UI routes/pages render.
- The intent-classifier enum mismatch in `router_chat.py` (`PATIENT_SPECIFIC_QUERY`) was identified as a runtime 500 cause and addressed.
- Local `/api/chat` reaches the ML pipeline when the backend is operational.

*(Note: While CORS errors were observed, it has not been definitively established if the root cause was genuinely CORS rather than a backend 500 being surfaced by the browser as a CORS symptom).*

## Known / Unverified
- [ ] Dependency changes independently audited
- [ ] NumPy / SciPy / Torch compatibility verified
- [ ] Transformers / sentence-transformers compatibility verified
- [ ] `bitsandbytes` necessity and runtime usage verified
- [ ] CORS root cause conclusively established
- [ ] OCR/LIFT document ingestion verified end-to-end
- [ ] Neo4j graph population verified from the real ingestion path
- [ ] Vector embedding/index population verified
- [ ] Retrieval verified against ingested document content
- [ ] Reranking verified
- [ ] Ollama/MedGemma generation verified
- [ ] Claim extraction verified
- [ ] Claim verification/evidence attribution verified
- [ ] Complete document-upload → grounded-answer flow verified
- [ ] E2E test completed against real data without mocks

*The current state does NOT yet constitute proof of complete real end-to-end functionality.*

## Dependency Changes Under Review
Dependency modifications were made during local debugging, but they have not yet been accepted as permanent repository changes. The following areas require a strict audit (checking original version, new version, motivating traceback, actual runtime usage, and compatibility constraints) before deciding whether to retain the change:

- **numpy**: Downgraded to `<2.0` due to runtime crashes with NumPy 1.x-compiled modules (e.g. older `torch` and `scipy`).
- **scipy**: Bound to older versions to avoid NumPy 2.x initialization issues.
- **torch**: Currently running `2.2.2`. Needs compatibility check against Transformers/NumPy limits.
- **transformers**: Downgraded to `<4.40.0` (specifically `4.39.3`) because `5.x` dropped support for PyTorch `2.2.2`, throwing false "PyTorch not found" errors in `import_utils.py`.
- **sentence-transformers**: Downgraded to `<2.6.0` (specifically `2.5.1`) as newer versions strictly require `transformers>=5.0.0`.
- **bitsandbytes**: Lowered version bounds (`<0.43.0`) to avoid pip dependency resolution blocks on ARM64 macOS wheels.

*Do not claim that ARM64 macOS incompatibility or a Transformers/PyTorch incompatibility is definitively established unless the repository evidence demonstrates it consistently across clean environments.*

## ML / Infrastructure Constraints
- Ollama requires the expected model to be explicitly available locally. The current default model is configured as `medgemma:4b`.
- Docker Desktop on Apple Silicon does not provide the same GPU environment as a Linux/NVIDIA deployment.
- Embedding, reranking, and LLM generation may therefore be very slow locally due to CPU execution.
- A long response time should be distinguished from an actual correctness/integration failure.

*Do NOT recommend introducing a mocked Ollama client as a fix for the real integration path. A mock may later be useful for isolated UI regression testing, but it must remain separate from acceptance testing of the real pipeline.*

## Neo4j / Ingestion
**Warning:** An empty Neo4j database means the graph-dependent portion of QA/RAG has not been meaningfully validated.

Before adding seed data or initialization hooks, trace the existing ingestion architecture and determine whether the repository already has an intended ingestion command (e.g. `ml/rag/ingest/run_ingest.py`). 

Do not introduce fake/seed clinical data merely to make the UI appear functional. The preferred validation path is:
`document upload → document processing → OCR/LIFT extraction → structured observations → chunking → embeddings/indexing → graph persistence where applicable → retrieval → reranking → QA generation → claim extraction → evidence verification → frontend response`

## Next Steps
1. Audit all dependency changes without modifying them.
2. Review the resulting `git diff` and classify each dependency change as KEEP / REVERT / NEEDS INVESTIGATION.
3. Trace the real document-ingestion path.
4. Verify Neo4j/vector-store population from that path.
5. Run a real document → retrieval → QA → verification flow.
6. Only after correctness is established, investigate local inference performance/timeouts.
7. Separately consider lightweight mocks for fast UI regression tests if useful.
8. Only after the integration is understood should PR #5 be formally merged.

## Git / Branch Safety
**This branch is a temporary integration workspace.** Do not:
- reset
- clean
- discard WIP
- switch branches
- pop/drop the original WIP stash
- commit unrelated changes
- push the branch

...unless explicitly instructed.
