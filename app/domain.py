from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentPage:
    source: str
    page: int
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    page: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Chunk":
        return cls(
            chunk_id=str(value["chunk_id"]),
            source=str(value["source"]),
            page=int(value["page"]),
            text=str(value["text"]),
        )


@dataclass(frozen=True)
class SearchHit:
    chunk: Chunk
    score: float
    lexical_score: float
    vector_score: float
    overlap_ratio: float

