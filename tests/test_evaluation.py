from pathlib import Path

from app.config import Settings
from app.evaluation import EvaluationCase, evaluate
from app.service import PlantOpsService


def test_evaluation_reports_retrieval_and_abstention_metrics(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, chunk_size=30, chunk_overlap=5)
    settings.ensure_directories()
    (settings.raw_dir / "manual.txt").write_text(
        "Disconnect and lock out power before inspection. "
        "Blocked ventilation can cause the motor to overheat.",
        encoding="utf-8",
    )
    service = PlantOpsService(settings)
    service.initialize()
    cases = [
        EvaluationCase(
            case_id="safety",
            question="What must I do before inspection?",
            answerable=True,
            expected_source="manual.txt",
            expected_phrases=("lock out power",),
        ),
        EvaluationCase(
            case_id="unknown",
            question="How do I repair the satellite antenna?",
            answerable=False,
            expected_source=None,
            expected_phrases=(),
        ),
    ]

    report = evaluate(service, cases, top_k=2)

    assert report["metrics"]["recall_at_2"] == 1.0
    assert report["metrics"]["mrr"] == 1.0
    assert report["metrics"]["abstention_accuracy"] == 1.0
    assert report["configuration"]["embedding_backend"] == "hash"
