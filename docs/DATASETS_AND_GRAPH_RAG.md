# PHIRE: Finalized Datasets, Models & Graph RAG Architecture

**Status**: Finalized decision, supersedes dataset references in `docs/OPEN_SOURCE_TOOLS.md` and `docs/FEATURES_ALIGNED.md` where they conflict
**Date**: August 2026
**Basis**: Column-level validation of every dataset previously referenced in PHIRE's docs and `ml/recommendations/` stubs, checked against primary sources (UCI, PhysioNet, MIT CSAIL, Google Research, Fordham WISDM Lab, vision.imar.ro, USDA), plus research into graph-based retrieval for the RAG layer

---

## 1. Why this document exists

Earlier docs named several *candidate* datasets without checking whether their actual columns, licenses, and access terms hold up. That check surfaced one factual error (Section 3) and several fit issues that change what should be built when. This document is the finalized answer: what PHIRE actually trains on, per component, and why.

---

## 2. Finalized dataset & model decisions

### 2.1 Fitness / activity recognition (tabular time-series ML)

| Role | Dataset | Why |
|---|---|---|
| **Pretrain** | PAMAP2 (UCI 231, CC BY 4.0) | 100Hz multi-IMU (wrist/chest/ankle) + HR, 18 activities. Rich feature space for a general activity representation. N=9 (8M/1F) is too small and skewed to ship directly. |
| **Fine-tune / deploy** | WISDM (Fordham WISDM Lab, free research use) | Single accelerometer at 20Hz, N=51 — matches a phone-pocket or wrist wearable far more closely than PAMAP2's 3-IMU rig. This is the feature space the shipped classifier should target, since it's what a real Fitbit/Oura/Apple Watch integration will actually deliver. |

**Model**: lightweight 1D-CNN or CNN-LSTM, quantized for local inference, pretrained on PAMAP2 and fine-tuned on WISDM. Neither dataset carries a form-quality signal — they classify *which* activity, not *how well it's performed*. Form feedback is a computer-vision problem (Section 2.4).

### 2.2 Nutrition — personalization & outcome data

| Role | Dataset | Why |
|---|---|---|
| **Primary personalization / outcome layer** | CGMacros (PhysioNet, **open access, no DUA**, CC BY-NC-SA 4.0) | 45 participants x 10 days: meal macros + food photos + two CGMs + Fitbit + biomarkers + gut microbiome, all timestamp-linked. A logged meal + its measured glucose response is a ready-made evidence pair — this is the closest existing dataset to PHIRE's "claim traceable to evidence" design goal applied to nutrition. |
| **Candidate, pending verification — not yet committed** | AI4FoodDB | 100-participant, 10-sub-dataset intervention (nutrition, anthropometrics, biomarkers, gut microbiome, sleep, activity, emotional state) is genuinely rich, but no public source publishes a column-level schema for DS3 (Nutrition). **Do not write ingestion code against it until the actual repository files have been opened and the schema confirmed.** |

**License flag**: CGMacros is CC BY-NC-SA 4.0 — fine for PHIRE's current research status, but the ShareAlike clause means any derivative dataset PHIRE publishes from it inherits the same non-commercial license. Revisit before any commercial pivot.

### 2.3 Nutrition — reference / evidence grounding

| Role | Dataset | Why |
|---|---|---|
| **Essential, not optional** | USDA FoodData Central (public domain) | 350,000+ foods, nutrient values per 100g, free API + bulk CSV/JSON. This is not training data — it's the lookup table every calorie/macro claim PHIRE makes should cite. Structurally identical to the `Observation` entity already in PHIRE's architecture (value, unit, date, source). **Ingest into `ml/rag/` as an evidence source independent of any recommendation model training**, matching Feature 7 (claim-level evidence attribution) directly. |

### 2.4 Nutrition — computer vision (food image → macros)

| Role | Dataset | Why |
|---|---|---|
| **Primary training set (calorie/macro regression)** | Nutrition5k (Google Research, **CC BY 4.0, commercial use OK**) | ~5,000 real dishes, physically weighed (not estimated). Clean CSV: `dish_id, total_calories, total_mass, total_fat, total_carb, total_protein, num_ingrs`, repeated per-ingredient. Directly trainable, no external join required. The strongest CV dataset validated in this audit. |
| **Pretraining / classification backbone only** | Food-101 (ETH Zurich, research use; images sourced via Foodspotting's own terms) | 101 categories x 1,000 images. Category labels only — no macros, no portion size. Use only to answer "what dish is this," then join to Nutrition5k/USDA for the actual nutrition claim. Do not treat as a macro ground truth. |
| **Recipe generation / recipe↔image linking** | Recipe1M+ (MIT CSAIL, request-gated, non-commercial) | 1M+ recipes with text + 13M+ images. Nutrition fields exist **only** for the subset where unit+quantity were both parsed — filter explicitly on non-null nutrition before use; the rest is a missing row, not a zero. |

### 2.5 Exercise posture & form (computer vision)

| Role | Dataset / Model | Why |
|---|---|---|
| **Pose estimation — run directly, no training** | MediaPipe Pose / BlazePose (Google, Apache 2.0) | 33 landmarks, x/y/z + visibility, <100ms on CPU. This **replaces the "train a custom pose model" line of work entirely** for MVP — compute joint angles (squat depth, elbow flexion) straight from its output, entirely on-device, which also satisfies the local-inference privacy boundary since no video needs to leave the device. |
| **Removed from the roadmap** | ~~Human3.6M~~ | `docs/OPEN_SOURCE_TOOLS.md` previously listed "HumanAI 3.6M: 3.6M 3D pose sequences (various exercises)." **This mischaracterizes the real dataset.** Human3.6M's 17 activities are indoor daily-life poses (talking on the phone, smoking, discussing) — there is no squat, push-up, lunge, or deadlift class. It is also academic-account-gated and explicitly non-redistributable, which conflicts with an open-source release goal. **Do not use.** |
| **MVP-only fine-tuning target** | Kaggle exercise-pose datasets (e.g. "Squat Exercise Pose Dataset") | Small, crowd-sourced, joint-angle-labeled sets (squat depth, forward lean, knee cave-in, heel lift). Useful to fine-tune a lightweight form-scoring classifier on top of MediaPipe's joint angles for an MVP demo. Each dataset needs its own license check; **do not** build the roadmap's "injury prevention alerts" claim on these alone without independent validation — soften that claim or back it with a proper study before shipping. |

### 2.6 Summary table

| Component | Foundation | Personalization | Grounding |
|---|---|---|---|
| Activity recognition | PAMAP2 (pretrain) | WISDM (fine-tune, real-hardware match) | — |
| Food identification | Nutrition5k / Food-101 backbone | User's logged meals over time | USDA FoodData Central |
| Calorie/macro estimation | Nutrition5k | CGMacros (outcome-linked) | USDA FoodData Central |
| Meal/recipe generation | Recipe1M+ (nutrition-filtered subset) | User dietary constraints/goals | USDA FoodData Central |
| Exercise form feedback | MediaPipe Pose (inference only) | Kaggle exercise-pose sets (MVP) | Computed joint angles |

---

## 3. Graph RAG: adding a third retrieval leg

### 3.1 Why vector search alone isn't enough

PHIRE's RAG layer (`ml/rag/`) currently combines BM25 (lexical) and dense embeddings via Chroma (semantic). Both are similarity-based: they answer "what's relevant to this query," not "how are these facts connected." That's a structural gap for two of PHIRE's own core research directions:

- **Longitudinal Health Reasoning** — "how has my LDL changed *relative to* my statin dose changes over 3 years" is a multi-hop, relational question. No amount of embedding similarity recovers the *chain* connecting a medication-start event to a lab-value trend two years later.
- **Contradiction-Aware Health RAG** — detecting that two records disagree requires comparing values across explicit `same_metric` / `conflicts_with` relationships, not ranking passages by similarity.

Published comparisons back this up: RAG wins single-hop, detail-oriented questions; graph-grounded retrieval wins multi-hop and relational ones, with one benchmark showing a knowledge-graph-grounded LLM improving from 16.7% to 56.2% accuracy on relational questions over the same model without graph grounding. Most production RAG stacks in 2026 combine both rather than picking one.

### 3.2 Tooling decision

| Tool | Role | Why |
|---|---|---|
| **LightRAG** (EMNLP 2025) | Primary graph-RAG library | Natively supports Ollama for entity/relationship extraction, so PHI never has to leave the local boundary during graph construction — this is the deciding factor over Microsoft GraphRAG, which is a heavier, batch-oriented, global-summarization design built around cloud LLM calls and less suited to real-time per-patient local queries. Published benchmarks show it outperforming naive RAG, HyDE, and Microsoft GraphRAG on retrieval accuracy and efficiency. Supports Neo4j as a storage backend. |
| **Neo4j** (community edition, self-hosted) | Graph storage | Already listed as PHIRE's candidate "graph layer" in the original architecture notes. Backs LightRAG's entity/relationship graph and directly represents the Longitudinal Health Graph (Observation / Medication / Condition / Claim nodes) sketched in the NLP-06 proposal's health-representation section. |
| Microsoft GraphRAG | Reference benchmark only, not adopted | Origin of the graph-RAG approach and a useful comparison point, but its cloud-oriented, global-summarization design is a worse fit than LightRAG for PHIRE's local, per-patient, low-latency requirement. |

### 3.3 Retrieval routing

Three-way hybrid retrieval, routed by question shape:

1. **Lexical (BM25)** — exact term/value matches ("LDL", "142 mg/dL").
2. **Semantic (Chroma vector search)** — paraphrase and similarity matches, single-document lookups.
3. **Graph traversal (LightRAG over Neo4j)** — multi-hop, relational, and longitudinal questions; also the natural mechanism for surfacing conflicting records, since a graph edge can encode `conflicts_with` or `supersedes` explicitly instead of relying on a re-ranking heuristic.

A useful side effect for the nutrition/fitness recommendation layer specifically: connecting `Observation` nodes (lab values, logged meals, activity sessions) to `Recommendation` nodes via explicit `supports` / `contraindicated_by` edges gives evidence attribution "for free" — the edge itself *is* the provenance link, consistent with PHIRE's core claim-to-evidence design rather than bolted on separately for recommendations.

### 3.4 What changes in the codebase

- `ml/rag/retriever.py` — updated to describe the three-way hybrid (see file).
- `ml/requirements.txt` — added `lightrag-hku` and `neo4j` as candidate (commented) dependencies, pending a Phase 2 spike.
- No change to MVP (Weeks 1-3) scope: BM25 + Chroma remains the Tier 0 baseline. Graph RAG is a Month 2-3 addition, consistent with the existing roadmap's "Contradiction-Aware Health RAG" and "Hybrid Structured + Semantic Retrieval" phase-2 items in `docs/AGGRESSIVE_ROADMAP.md`.

---

## 4. Corrections to existing docs

- `docs/OPEN_SOURCE_TOOLS.md` — "HumanAI 3.6M" entry corrected/removed (Section 2.5 above); Nutrition5k elevated to primary CV nutrition dataset; graph RAG tooling added.
- `docs/FEATURES_ALIGNED.md` — Features 10-15 (CV) and Feature 18 (Hybrid Structured + Semantic Retrieval) updated to reflect the finalized datasets and the graph RAG addition.
