from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = PROJECT_ROOT / "data"
    top_k: int = 5
    min_score: float = 0.20
    chunk_size: int = 180
    chunk_overlap: int = 35
    generator: str = "extractive"
    embedding_backend: str = "hash"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    llm_timeout_seconds: float = 30.0
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    openai_base_url: str = "https://api.openai.com"
    openai_model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None
    max_upload_bytes: int = 10_000_000
    allow_uploads: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("PLANTOPS_DATA_DIR", PROJECT_ROOT / "data")),
            top_k=int(os.getenv("PLANTOPS_TOP_K", "5")),
            min_score=float(os.getenv("PLANTOPS_MIN_SCORE", "0.20")),
            chunk_size=int(os.getenv("PLANTOPS_CHUNK_SIZE", "180")),
            chunk_overlap=int(os.getenv("PLANTOPS_CHUNK_OVERLAP", "35")),
            generator=os.getenv("PLANTOPS_GENERATOR", "extractive"),
            embedding_backend=os.getenv("PLANTOPS_EMBEDDING_BACKEND", "hash"),
            embedding_model=os.getenv(
                "PLANTOPS_EMBEDDING_MODEL",
                "BAAI/bge-small-en-v1.5",
            ),
            llm_timeout_seconds=float(
                os.getenv("PLANTOPS_LLM_TIMEOUT_SECONDS", "30")
            ),
            ollama_base_url=os.getenv(
                "PLANTOPS_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ),
            ollama_model=os.getenv("PLANTOPS_OLLAMA_MODEL", "llama3.2:3b"),
            openai_base_url=os.getenv(
                "PLANTOPS_OPENAI_BASE_URL", "https://api.openai.com"
            ),
            openai_model=os.getenv("PLANTOPS_OPENAI_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("PLANTOPS_OPENAI_API_KEY"),
            max_upload_bytes=int(
                os.getenv("PLANTOPS_MAX_UPLOAD_BYTES", "10000000")
            ),
            allow_uploads=os.getenv("PLANTOPS_ALLOW_UPLOADS", "true").lower()
            in {"1", "true", "yes", "on"},
        )

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def index_path(self) -> Path:
        return self.data_dir / "index" / "chunks.json"

    @property
    def feedback_path(self) -> Path:
        return self.data_dir / "feedback" / "feedback.jsonl"

    def ensure_directories(self) -> None:
        for directory in (
            self.raw_dir,
            self.upload_dir,
            self.index_path.parent,
            self.feedback_path.parent,
            self.model_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @property
    def model_dir(self) -> Path:
        return self.data_dir / "models"

