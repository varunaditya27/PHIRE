# Running PHIRE on a CPU-only laptop

PHIRE's default setup assumes an NVIDIA GPU. This guide is for a machine **without** one, such as most
laptops. Everything runs locally and nothing about privacy changes; it is just slower, and documents are
read by a different model.

## What is different on CPU

| | GPU variant (default) | CPU variant |
|---|---|---|
| Reading uploaded documents | `datalab-to/lift` (9.7B vision model, 4-bit, ~6.5GiB of VRAM) | An **Ollama vision model** (`medgemma:4b`, the same model that answers chat — nothing extra to download) fed each page's image plus its PDF text layer |
| Embeddings, reranker, claim verifier | on the GPU (verifier in fp16) | on the CPU (fp32) |
| Chat model | `medgemma:4b` via Ollama | `medgemma:4b` via Ollama (quantized; runs on CPU) |
| Backend Docker image | ~11GB (PyTorch CUDA wheels + lift) | **~2.7GB** (CPU-only PyTorch, no lift) |
| Selected by | an NVIDIA container runtime being present | no NVIDIA runtime (or `PHIRE_VARIANT=cpu`) |

lift is not offered on CPU on purpose: it is 18GB of weights and minutes per page, which no ordinary laptop
can host. The vision-model path produces the same structured result (same schema, same downstream
pipeline), so the dashboard, chat, citations, graph retrieval and everything else behave identically.

## Hardware

PHIRE keeps several models in RAM on a CPU machine: the two MedCPT encoders and a cross-encoder (~0.4GB
each), BART-large-MNLI (~1.6GB in fp32), and Ollama's `medgemma:4b` (~3.3GB quantized, plus its vision
encoder and context), alongside PostgreSQL, Neo4j and the frontend.

| RAM (estimated from the component sizes above) | Verdict |
|---|---|
| 8GB | Not recommended — it will swap or run out of memory when a document is processed |
| 12GB | Works for light use; close other apps |
| **16GB or more** | **Recommended** |

You also need roughly 10GB of free disk for the images and models, and a multi-core CPU (the more cores,
the faster everything is). Docker with Compose v2 is required for the Docker path.

## Setup (Docker — recommended)

1. **Install Ollama** on the machine (not in Docker): <https://ollama.com/download> (Linux:
   `curl -fsSL https://ollama.com/install.sh | sh`; macOS and Windows have installers).
2. **Pull the model once:** `ollama pull medgemma:4b`
3. **Start PHIRE:**
   ```bash
   git clone https://github.com/varunaditya27/PHIRE.git && cd PHIRE
   bash scripts/run.sh
   ```
   `scripts/run.sh` detects that there is no NVIDIA runtime and selects the CPU variant automatically (it
   prints `CPU variant`). The first build downloads CPU-only PyTorch and the dependencies; the first chat
   downloads the small embedding/verification models from Hugging Face (weights only — no patient data
   leaves your machine). To force it: `PHIRE_VARIANT=cpu bash scripts/run.sh`.
4. **Seed the public reference corpus once** (MedlinePlus/PubMed/USDA evidence the verifier checks general
   statements against; needs the network):
   ```bash
   docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.cpu.yml \
     --profile ingest run --rm ingest
   ```
5. Open <http://localhost:3000>, upload a document on the **Documents** page, and ask questions on **Chat**.

If you have no Ollama on the host at all, `scripts/run.sh` starts a bundled Ollama container instead (and
pulls `medgemma:4b` into it); installing Ollama natively is lighter and is what we test.

## Setup (without Docker, for development)

```bash
bash scripts/setup.sh           # detects no GPU: installs CPU-only PyTorch, skips lift
# start PostgreSQL and Neo4j yourself (see backend/README.md), fill backend/.env, then:
bash scripts/run_backend.sh     # PHIRE_EXTRACTOR=auto resolves to the Ollama vision model without CUDA
bash scripts/run_frontend.sh
```

Requirements files: `ml/requirements.txt` is the CPU-safe base; `ml/requirements-lift.txt` is the GPU-only
extra that the CPU setup skips.

## What to expect (measured)

Measured with Ollama forced onto the CPU (`num_gpu: 0`) on an AMD Ryzen 7 260 (8 cores / 16 threads), which is
a fairly strong laptop-class CPU — **a typical laptop may be 1.5–3x slower**:

| Action | Time |
|---|---|
| Reading a one-page document (image + text layer) | **~110–135s** per page, same accuracy as on a GPU for the test documents |
| A chat answer (typical, 1–3 claims) | **~40–70s**: retrieval ~4s, draft ~23s, claim extraction ~10s, claim verification ~6–7s per claim |
| First request after startup | extra time to load models |

The progress panels in the app show each stage live, so a slow step never looks frozen. Upload documents one
at a time and let each finish. Long generations are fine: the backend's Ollama timeout is raised to 10 minutes
in the CPU variant (`OLLAMA_TIMEOUT_SECONDS`), and the per-page extraction timeout is
`OLLAMA_VISION_TIMEOUT_SECONDS` (default 600).

## Accuracy: what is worth knowing

A 4B vision model is less robust than lift on difficult layouts. On the test documents (a digital PDF, a
degraded rotated scan, and a form with composite readings) it extracted every lab value, unit, blood
pressure, height and visual-acuity reading, and every date, correctly — but on the noisy scan it missed one
medication and one diagnosis. In practice:

- **Digital PDFs are the best case**: the page's own text layer is passed to the model, which makes them very
  reliable. Prefer the original PDF over a photo of it.
- **Photos and scans** work for clearly printed reports; handwriting, glare and heavy skew are risky.
- **Check what was extracted**: the Dashboard shows every reading with its source document; a wrong or
  missing value there means the document should be re-uploaded (or the file improved).
- If **no date** can be found, PHIRE asks you for it on the Documents page instead of guessing.

## Changing the model or the extractor

- `OLLAMA_MODEL` (chat) and `OLLAMA_VISION_MODEL` (extraction, defaults to `OLLAMA_MODEL`) accept any
  Ollama tag; the vision one must be multimodal. A larger model reads better but needs more RAM and time.
- `PHIRE_EXTRACTOR=auto|lift|ollama` — `auto` uses lift only when a CUDA GPU and `lift-pdf` are present. Set
  `ollama` on a GPU machine that wants its VRAM for chat only.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Vision extraction via Ollama … failed` / timeout | The model took longer than the timeout on a slow CPU — raise `OLLAMA_VISION_TIMEOUT_SECONDS`; check `ollama ps` |
| Chat returns an Ollama error | `ollama pull medgemma:4b`; make sure Ollama is running (`curl localhost:11434/api/tags`) |
| Container or models killed / very slow, disk or RAM full | Not enough RAM (see Hardware); close other applications |
| `scripts/run.sh` says GPU variant on a laptop with a discrete GPU you don't want to use | `PHIRE_VARIANT=cpu bash scripts/run.sh` |

## Platform note

The backend container uses host networking (it is how PHIRE's local-only privacy guard accepts the Ollama and
Neo4j addresses), which is native on Linux. On macOS or Windows Docker Desktop it needs the host-networking
option (Docker Desktop 4.29+, Settings → Resources → Network); otherwise run without Docker as above.
