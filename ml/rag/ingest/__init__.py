"""
Reference-evidence ingestion for ml/rag/.

Pulls fully-public, freely-licensed reference material into the Chroma +
BM25 indices retriever.py searches: PubMed abstracts and MedlinePlus
consumer-health summaries (clinical reference docs), plus USDA FoodData
Central (nutrition evidence, per docs/DATASETS_AND_GRAPH_RAG.md section
2.3). Entry point is run_ingest.py. This only ever touches public
reference data, never patient data — PHIRE's "no cloud APIs for patient
data" boundary is about PHI, not about fetching a public NIH/USDA corpus
once at setup time.
"""
