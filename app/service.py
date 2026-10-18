from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.domain import Chunk
from app.generation import ExtractiveAnswerGenerator, GroundedLLMGenerator
from app.ingestion import chunk_pages, discover_documents, load_pages
from app.repository import IndexRepository
from app.retrieval import HybridRetriever
from app.providers import HTTPJSONClient, OllamaProvider, OpenAICompatibleProvider
from app.schemas import Citation, DocumentSummary, QueryResponse


LIVE_STATE_PATTERN = re.compile(
    r"\b(live|real[- ]?time|right now|currently|latest)\b",
    re.IGNORECASE,
)
LIVE_SIGNAL_PATTERN = re.compile(
    r"\b(reading|telemetry|status|value|measurement|temperature|pressure|"
    r"vibration|current|voltage|speed|rpm)\b",
    re.IGNORECASE,
)


def requests_live_equipment_state(question: str) -> bool:
    """Return true when a question requires telemetry that documents cannot provide."""
    return bool(
        LIVE_STATE_PATTERN.search(question) and LIVE_SIGNAL_PATTERN.search(question)
    )


class PlantOpsService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.repository = IndexRepository(settings.index_path)
        self.chunks: list[Chunk] = []
        self.retriever = HybridRetriever([])
        self.generator = self._build_generator()

    def _build_generator(self) -> ExtractiveAnswerGenerator | GroundedLLMGenerator:
        if self.settings.generator == "extractive":
            return ExtractiveAnswerGenerator()

        client = HTTPJSONClient(self.settings.llm_timeout_seconds)
        if self.settings.generator == "ollama":
            provider = OllamaProvider(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_model,
                client=client,
            )
            return GroundedLLMGenerator(provider)

        if self.settings.generator == "openai-compatible":
            provider = OpenAICompatibleProvider(
                base_url=self.settings.openai_base_url,
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                client=client,
            )
            return GroundedLLMGenerator(provider)

        raise ValueError(
            f"Unsupported generator: {self.settings.generator}. "
            "Choose 'extractive', 'ollama', or 'openai-compatible'."
        )

    def initialize(self) -> None:
        self.settings.ensure_directories()
        self.chunks = self.repository.load()
        if not self.chunks:
            self.ingest_all()
        else:
            self.retriever = HybridRetriever(
                self.chunks,
                embedding_backend=self.settings.embedding_backend,
                embedding_model=self.settings.embedding_model,
                embedding_cache_dir=str(self.settings.model_dir),
            )

    def ingest_all(self) -> tuple[int, int, list[str]]:
        paths = discover_documents(self.settings.raw_dir) + discover_documents(
            self.settings.upload_dir
        )
        chunks: list[Chunk] = []
        for path in paths:
            chunks.extend(
                chunk_pages(
                    load_pages(path),
                    chunk_size=self.settings.chunk_size,
                    overlap=self.settings.chunk_overlap,
                )
            )

        self.chunks = chunks
        self.repository.save(chunks)
        self.retriever = HybridRetriever(
            chunks,
            embedding_backend=self.settings.embedding_backend,
            embedding_model=self.settings.embedding_model,
            embedding_cache_dir=str(self.settings.model_dir),
        )
        sources = sorted({chunk.source for chunk in chunks})
        return len(paths), len(chunks), sources

    def store_upload(self, filename: str, content: bytes) -> Path:
        safe_name = Path(filename).name
        if Path(safe_name).suffix.lower() not in {".txt", ".md", ".pdf"}:
            raise ValueError("Only .txt, .md and .pdf files are supported")
        destination = self.settings.upload_dir / safe_name
        destination.write_bytes(content)
        return destination

    def query(self, question: str, top_k: int | None = None) -> QueryResponse:
        if requests_live_equipment_state(question):
            return QueryResponse(
                answer=(
                    "I cannot access live equipment telemetry. I can only answer from "
                    "the indexed maintenance documents."
                ),
                citations=[],
                confidence=0.0,
                abstained=True,
                generator=self.generator.name,
            )

        hits = self.retriever.search(question, top_k or self.settings.top_k)
        relative_floor = hits[0].score * 0.45 if hits else 0.0
        supported = [
            hit
            for hit in hits
            if hit.score >= max(self.settings.min_score, relative_floor)
            and hit.overlap_ratio > 0
        ]
        if not supported:
            return QueryResponse(
                answer=(
                    "I do not have enough evidence in the indexed maintenance documents "
                    "to answer that question safely."
                ),
                citations=[],
                confidence=0.0,
                abstained=True,
                generator=self.generator.name,
            )

        generation = self.generator.generate(question, supported)
        if not generation.cited_hits:
            return QueryResponse(
                answer=generation.answer,
                citations=[],
                confidence=0.0,
                abstained=True,
                generator=generation.generator,
            )

        citations = [
            Citation(
                citation_id=index,
                source=hit.chunk.source,
                page=hit.chunk.page,
                chunk_id=hit.chunk.chunk_id,
                excerpt=hit.chunk.text[:320],
                score=round(hit.score, 4),
            )
            for index, hit in enumerate(generation.cited_hits, start=1)
        ]
        confidence = sum(hit.score for hit in generation.cited_hits) / len(
            generation.cited_hits
        )
        return QueryResponse(
            answer=generation.answer,
            citations=citations,
            confidence=round(confidence, 4),
            abstained=False,
            generator=generation.generator,
        )

    def document_summaries(self) -> list[DocumentSummary]:
        counts = Counter(chunk.source for chunk in self.chunks)
        return [
            DocumentSummary(source=source, chunks=count)
            for source, count in sorted(counts.items())
        ]

    def store_feedback(self, payload: dict[str, object]) -> None:
        self.settings.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        record = {"timestamp": datetime.now(UTC).isoformat(), **payload}
        with self.settings.feedback_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

