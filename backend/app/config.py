"""
Application settings, loaded from environment variables (see .env.example).

Single source of truth for config — no other module should read
os.environ directly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> parents[2] is the repo root -- same
# REPO_ROOT/data/chroma convention ml/rag/retriever.py's own
# DEFAULT_CHROMA_DIR uses (Path(__file__).resolve().parents[2] there
# too, from ml/rag/retriever.py). Anchored to the repo root, not cwd, so
# backend and ml/ resolve to the identical physical Chroma store
# regardless of which directory either process is launched from --
# a naive "./data/chroma" default silently diverges the moment either
# side is run from a different cwd.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database (PostgreSQL + pgvector) ---
    database_url: str = "postgresql+psycopg2://phire:phire@localhost:5432/phire"

    # --- Ollama ---
    # medgemma:4b is the only tag ml/ actually pulls (see
    # ml/llm/ollama_client.py) -- medgemma ships 4B/27B, not 8B.
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "medgemma:4b"
    ollama_timeout_seconds: float = 30.0

    # --- Legacy model config (deprecated; superseded by Lift VLM) ---
    ocr_model: str = "olmocr"
    prose_extraction_model: str = "qwen3.5:9b"

    # --- Lift VLM ---
    lift_model: str = Field(default="datalab-to/lift", validation_alias="LIFT_MODEL")
    lift_device: str = Field(default="auto", validation_alias="LIFT_DEVICE")
    phire_mock_lift: bool = Field(default=True, validation_alias="PHIRE_MOCK_LIFT")

    # --- Neo4j (ml/graph -- Longitudinal Health Graph) ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # --- Vector store (Chroma, in-process) ---
    # Resolved relative to the repo root by ml/rag/retriever.py itself
    # (see its REPO_ROOT/DEFAULT_CHROMA_DIR) when CHROMA_PERSIST_DIR is
    # unset -- set explicitly here so backend and ml/ always agree on one
    # physical Chroma store instead of each resolving their own relative
    # path from a different process cwd.
    chroma_persist_dir: str = str(_REPO_ROOT / "data" / "chroma")
    chroma_collection: str = "phire_evidence"

    # --- CORS ---
    # When allow_credentials=True, '*' is not permitted. Specify explicit development origins.
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:3001"])

    # --- Uploads ---
    upload_dir: str = "./data/documents"
    upload_max_size_bytes: int = 25 * 1024 * 1024  # 25MB

    # --- Security ---
    encryption_key: str = ""  # Fernet key; required in production, see utils/encryption.py
    audit_log_path: str = "./data/audit.log"

    # --- App ---
    environment: str = "development"



def get_settings() -> Settings:
    settings = Settings()
    # Debug: log CORS origins to verify they're loaded correctly
    print(f"[Config] CORS origins loaded: {settings.cors_origins}")
    return settings
