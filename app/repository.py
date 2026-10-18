from __future__ import annotations

import json
from pathlib import Path

from app.domain import Chunk


class IndexRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, chunks: list[Chunk]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [chunk.to_dict() for chunk in chunks]
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def load(self) -> list[Chunk]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [Chunk.from_dict(item) for item in payload]

