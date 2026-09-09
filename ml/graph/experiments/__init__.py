"""
Prose-extraction method/model-selection experiment evaluating earlier
free-text fact extraction (evaluating qwen3.5:9b vs langextract).
Note: Production pipeline has since superseded both with unified visual
extraction via datalab-to/lift 9.7B VLM.

See RESULTS.md for methodology, historical results, and decisions. Run via:
    ml/.venv/bin/python -m ml.graph.experiments.run_benchmark
"""
