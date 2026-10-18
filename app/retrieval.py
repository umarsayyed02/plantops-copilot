from __future__ import annotations

import hashlib
import math
import os
import re
from collections import Counter
from pathlib import Path

from app.domain import Chunk, SearchHit


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]+")
STOPWORDS = {
    "a",
    "after",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "by",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "manual",
    "much",
    "no",
    "not",
    "of",
    "on",
    "or",
    "should",
    "the",
    "too",
    "to",
    "use",
    "what",
    "when",
    "where",
    "which",
    "why",
    "would",
    "with",
}

TOKEN_ALIASES = {
    "greasing": "grease",
    "hot": "temperature",
    "measured": "measure",
    "measurement": "measure",
    "measurements": "measure",
    "measuring": "measure",
    "monitored": "monitor",
    "monitoring": "monitor",
    "monitors": "monitor",
    "over-greasing": "grease",
    "overgreasing": "grease",
    "overheating": "overheat",
    "restarted": "restart",
    "restarting": "restart",
}


def tokenize(text: str) -> list[str]:
    def normalize(token: str) -> str:
        token = token.lower()
        if token in TOKEN_ALIASES:
            return TOKEN_ALIASES[token]
        # Small, dependency-free morphology normalizer for maintenance terms.
        # It aligns forms such as overheat/overheating and cause/caused/causes
        # without attempting to be a general-purpose language stemmer.
        if len(token) > 5 and token.endswith("ing"):
            token = token[:-3]
        elif len(token) > 4 and token.endswith("ed"):
            token = token[:-1] if token[-2] == "e" else token[:-2]
        elif len(token) > 4 and token.endswith("es"):
            token = token[:-1] if token[-2] == "e" else token[:-2]
        elif len(token) > 3 and token.endswith("s"):
            token = token[:-1]
        return token

    normalized: list[str] = []
    for raw_token in TOKEN_PATTERN.findall(text):
        candidates = [raw_token]
        if "-" in raw_token:
            candidates.extend(part for part in raw_token.split("-") if part)
        seen_candidates: set[str] = set()
        for candidate in candidates:
            if candidate.lower() in STOPWORDS:
                continue
            token = normalize(candidate)
            if token and token not in seen_candidates:
                normalized.append(token)
                seen_candidates.add(token)
    return normalized


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(chunk.text) for chunk in chunks]
        self.term_frequencies = [Counter(tokens) for tokens in self.tokens]
        self.doc_frequency: Counter[str] = Counter()
        for tokens in self.tokens:
            self.doc_frequency.update(set(tokens))
        self.average_length = (
            sum(len(tokens) for tokens in self.tokens) / len(self.tokens)
            if self.tokens
            else 1.0
        )

    def scores(self, query: str) -> list[float]:
        query_tokens = tokenize(query)
        total_documents = len(self.chunks)
        scores: list[float] = []
        for tokens, frequencies in zip(self.tokens, self.term_frequencies, strict=True):
            score = 0.0
            for term in query_tokens:
                frequency = frequencies[term]
                if not frequency:
                    continue
                document_frequency = self.doc_frequency[term]
                inverse_document_frequency = math.log(
                    1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                length_normalization = 1 - self.b + self.b * len(tokens) / self.average_length
                score += inverse_document_frequency * (
                    frequency * (self.k1 + 1)
                ) / (frequency + self.k1 * length_normalization)
            scores.append(score)
        return scores


class HashingVectorIndex:
    """Offline vector baseline. Replace with a sentence-transformer in milestone 2."""

    def __init__(self, chunks: list[Chunk], dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self.vectors = [self._vectorize(chunk.text) for chunk in chunks]

    def _feature_index(self, feature: str) -> int:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dimensions

    def _vectorize(self, text: str) -> dict[int, float]:
        tokens = tokenize(text)
        features = tokens + [f"{left}::{right}" for left, right in zip(tokens, tokens[1:])]
        values: Counter[int] = Counter(self._feature_index(feature) for feature in features)
        norm = math.sqrt(sum(value * value for value in values.values())) or 1.0
        return {index: value / norm for index, value in values.items()}

    @staticmethod
    def _dot(left: dict[int, float], right: dict[int, float]) -> float:
        if len(left) > len(right):
            left, right = right, left
        return sum(value * right.get(index, 0.0) for index, value in left.items())

    def scores(self, query: str) -> list[float]:
        query_vector = self._vectorize(query)
        return [self._dot(query_vector, vector) for vector in self.vectors]


class SentenceTransformerIndex:
    """Dense semantic retrieval using a locally cached sentence-transformer."""

    def __init__(self, chunks: list[Chunk], model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "The sentence-transformers backend is not installed. "
                "Run: python -m pip install -r requirements-semantic.txt"
            ) from exc

        self.model = SentenceTransformer(model_name)
        self.vectors = self.model.encode(
            [chunk.text for chunk in chunks],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def scores(self, query: str) -> list[float]:
        if len(self.vectors) == 0:
            return []
        query_vector = self.model.encode(
            query, normalize_embeddings=True, show_progress_bar=False
        )
        return [float(vector @ query_vector) for vector in self.vectors]


class FastEmbedIndex:
    """Dense semantic retrieval using a lightweight ONNX embedding runtime."""

    def __init__(self, chunks: list[Chunk], model_name: str, cache_dir: str | None) -> None:
        if cache_dir:
            cache_path = Path(cache_dir)
            os.environ.setdefault("HF_HOME", str(cache_path / "huggingface"))
            os.environ.setdefault("XDG_CACHE_HOME", str(cache_path / "cache"))
            os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "The fastembed backend is not installed. "
                "Run: python -m pip install -r requirements-semantic.txt"
            ) from exc

        self.model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        self.vectors = list(self.model.embed([chunk.text for chunk in chunks]))

    def scores(self, query: str) -> list[float]:
        if not self.vectors:
            return []
        query_vector = next(iter(self.model.embed([query])))
        return [float(vector @ query_vector) for vector in self.vectors]


class HybridRetriever:
    def __init__(
        self,
        chunks: list[Chunk],
        lexical_weight: float = 0.60,
        embedding_backend: str = "hash",
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        embedding_cache_dir: str | None = None,
    ) -> None:
        self.chunks = chunks
        self.lexical_weight = lexical_weight
        self.embedding_backend = embedding_backend
        self.bm25 = BM25Index(chunks)
        if embedding_backend == "hash":
            self.vectors = HashingVectorIndex(chunks)
        elif embedding_backend == "sentence-transformers":
            self.vectors = SentenceTransformerIndex(chunks, embedding_model)
        elif embedding_backend == "fastembed":
            self.vectors = FastEmbedIndex(chunks, embedding_model, embedding_cache_dir)
        else:
            raise ValueError(
                f"Unsupported embedding backend: {embedding_backend}. "
                "Choose 'hash', 'fastembed', or 'sentence-transformers'."
            )

    @staticmethod
    def _normalize(scores: list[float]) -> list[float]:
        maximum = max(scores, default=0.0)
        if maximum <= 0:
            return [0.0 for _ in scores]
        return [score / maximum for score in scores]

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        if not self.chunks:
            return []

        lexical = self.bm25.scores(query)
        vector = self.vectors.scores(query)
        normalized_lexical = self._normalize(lexical)
        normalized_vector = self._normalize(vector)
        query_terms = set(tokenize(query))

        hits: list[SearchHit] = []
        for index, chunk in enumerate(self.chunks):
            chunk_terms = set(tokenize(chunk.text))
            overlap = len(query_terms & chunk_terms) / max(len(query_terms), 1)
            hybrid = (
                self.lexical_weight * normalized_lexical[index]
                + (1 - self.lexical_weight) * normalized_vector[index]
            )
            # Keep the final score calibrated to [0, 1]. A weighted overlap
            # signal breaks semantic ties without saturating several hits at 1.0.
            reranked_score = 0.85 * hybrid + 0.15 * overlap
            hits.append(
                SearchHit(
                    chunk=chunk,
                    score=reranked_score,
                    lexical_score=normalized_lexical[index],
                    vector_score=normalized_vector[index],
                    overlap_ratio=overlap,
                )
            )

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]

