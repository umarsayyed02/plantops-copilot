from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class Citation(BaseModel):
    citation_id: int
    source: str
    page: int
    chunk_id: str
    excerpt: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float
    abstained: bool
    generator: str


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    sources: list[str]


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    answer: str = Field(min_length=1, max_length=10_000)
    rating: Literal["positive", "negative"]
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    stored: bool


class HealthResponse(BaseModel):
    status: str
    chunks: int
    generator: str
    embedding_backend: str
    uploads_enabled: bool


class DocumentSummary(BaseModel):
    source: str
    chunks: int


class BenchmarkMetrics(BaseModel):
    recall_at_5: float
    mrr: float
    abstention_accuracy: float
    citation_precision: float
    latency_p50_ms: float
    latency_p95_ms: float


class BenchmarkResult(BaseModel):
    name: str
    label: str
    metrics: BenchmarkMetrics


class BenchmarkResponse(BaseModel):
    benchmark_date: str
    dataset: str
    corpus: str
    results: list[BenchmarkResult]
    note: str

