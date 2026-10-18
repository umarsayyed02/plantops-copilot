from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, Settings
from app.domain import SearchHit
from app.service import PlantOpsService


DEFAULT_DATASET = PROJECT_ROOT / "evaluation" / "questions.json"
DEFAULT_REPORT = PROJECT_ROOT / "evaluation" / "reports" / "latest.json"


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    answerable: bool
    expected_source: str | None
    expected_phrases: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvaluationCase":
        return cls(
            case_id=str(value["id"]),
            question=str(value["question"]),
            answerable=bool(value["answerable"]),
            expected_source=value.get("expected_source"),
            expected_phrases=tuple(value.get("expected_phrases", [])),
        )


def load_dataset(path: Path) -> list[EvaluationCase]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationCase.from_dict(item) for item in payload]


def hit_is_relevant(hit: SearchHit, case: EvaluationCase) -> bool:
    if case.expected_source and hit.chunk.source != case.expected_source:
        return False
    lowered = hit.chunk.text.lower()
    return any(phrase.lower() in lowered for phrase in case.expected_phrases)


def evaluate(
    service: PlantOpsService,
    cases: list[EvaluationCase],
    top_k: int = 5,
) -> dict[str, Any]:
    answerable_count = sum(case.answerable for case in cases)
    reciprocal_rank_total = 0.0
    retrieved_relevant = 0
    abstention_correct = 0
    relevant_citations = 0
    total_citations = 0
    latencies_ms: list[float] = []
    details: list[dict[str, Any]] = []

    for case in cases:
        started = time.perf_counter()
        hits = service.retriever.search(case.question, top_k=top_k)
        response = service.query(case.question, top_k=top_k)
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies_ms.append(elapsed_ms)

        relevant_rank: int | None = None
        if case.answerable:
            for rank, hit in enumerate(hits, start=1):
                if hit_is_relevant(hit, case):
                    relevant_rank = rank
                    break
            if relevant_rank is not None:
                retrieved_relevant += 1
                reciprocal_rank_total += 1 / relevant_rank

        predicted_answerable = not response.abstained
        if predicted_answerable == case.answerable:
            abstention_correct += 1

        cited_chunk_ids = {citation.chunk_id for citation in response.citations}
        cited_hits = [hit for hit in hits if hit.chunk.chunk_id in cited_chunk_ids]
        if case.answerable:
            total_citations += len(cited_hits)
            relevant_citations += sum(hit_is_relevant(hit, case) for hit in cited_hits)

        details.append(
            {
                "id": case.case_id,
                "question": case.question,
                "answerable": case.answerable,
                "abstained": response.abstained,
                "relevant_rank": relevant_rank,
                "citation_count": len(response.citations),
                "latency_ms": round(elapsed_ms, 3),
            }
        )

    ordered_latencies = sorted(latencies_ms)

    def percentile(fraction: float) -> float:
        if not ordered_latencies:
            return 0.0
        index = round((len(ordered_latencies) - 1) * fraction)
        return ordered_latencies[index]

    return {
        "configuration": {
            "embedding_backend": service.settings.embedding_backend,
            "embedding_model": service.settings.embedding_model,
            "top_k": top_k,
            "cases": len(cases),
        },
        "metrics": {
            f"recall_at_{top_k}": round(
                retrieved_relevant / max(answerable_count, 1), 4
            ),
            "mrr": round(reciprocal_rank_total / max(answerable_count, 1), 4),
            "abstention_accuracy": round(
                abstention_correct / max(len(cases), 1), 4
            ),
            "citation_precision": round(
                relevant_citations / max(total_citations, 1), 4
            ),
            "latency_p50_ms": round(percentile(0.50), 3),
            "latency_p95_ms": round(percentile(0.95), 3),
        },
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate PlantOps retrieval and answers")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--top-k", type=int, default=5)
    arguments = parser.parse_args()

    settings = Settings.from_env()
    service = PlantOpsService(settings)
    service.initialize()
    report = evaluate(service, load_dataset(arguments.dataset), top_k=arguments.top_k)

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved report to {arguments.output}")


if __name__ == "__main__":
    main()

