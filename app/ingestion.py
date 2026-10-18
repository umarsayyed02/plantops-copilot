from __future__ import annotations

import hashlib
import re
from pathlib import Path

from app.domain import Chunk, DocumentPage


SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf"}


def load_pages(path: Path) -> list[DocumentPage]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("Install pypdf to ingest PDF documents") from exc

        reader = PdfReader(str(path))
        return [
            DocumentPage(source=path.name, page=number, text=page.extract_text() or "")
            for number, page in enumerate(reader.pages, start=1)
        ]

    return [DocumentPage(source=path.name, page=1, text=path.read_text(encoding="utf-8"))]


def discover_documents(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def chunk_pages(
    pages: list[DocumentPage], chunk_size: int = 180, overlap: int = 35
) -> list[Chunk]:
    if overlap >= chunk_size:
        raise ValueError("chunk overlap must be smaller than chunk size")

    chunks: list[Chunk] = []
    step = chunk_size - overlap

    for page in pages:
        cleaned = re.sub(r"\s+", " ", page.text).strip()
        words = cleaned.split()
        if not words:
            continue

        for start in range(0, len(words), step):
            text = " ".join(words[start : start + chunk_size])
            if not text:
                continue
            digest = hashlib.sha1(
                f"{page.source}:{page.page}:{start}:{text}".encode("utf-8")
            ).hexdigest()[:16]
            chunks.append(
                Chunk(
                    chunk_id=digest,
                    source=page.source,
                    page=page.page,
                    text=text,
                )
            )
            if start + chunk_size >= len(words):
                break

    return chunks

