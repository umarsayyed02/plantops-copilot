from pathlib import Path

from app.config import Settings
from app.service import PlantOpsService


MANUAL = """
# Pump Maintenance
Pump overheating may be caused by blocked ventilation, overload, or bearing friction.
Disconnect and lock out power before inspection. First compare the measured current on all phases
with the nameplate current and measure phase-to-phase voltage.
High vibration may indicate loose mounting bolts, shaft misalignment, or a damaged bearing.
Over-greasing can increase bearing temperature.
After restarting, monitor current, voltage, temperature, and vibration for fifteen minutes.
"""


def build_service(tmp_path: Path) -> PlantOpsService:
    settings = Settings(data_dir=tmp_path, chunk_size=40, chunk_overlap=5)
    settings.ensure_directories()
    (settings.raw_dir / "pump_manual.md").write_text(MANUAL, encoding="utf-8")
    service = PlantOpsService(settings)
    service.initialize()
    return service


def test_query_returns_supported_answer_and_citation(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query("Why is the pump overheating?")

    assert response.abstained is False
    assert response.citations
    assert response.citations[0].source == "pump_manual.md"
    assert "overheating" in response.answer.lower()


def test_query_abstains_when_documents_have_no_evidence(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query("How do I configure satellite telemetry encryption?")

    assert response.abstained is True
    assert response.citations == []
    assert response.confidence == 0.0


def test_question_words_do_not_count_as_document_evidence(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query("How do I configure satellite telemetry encryption?")

    assert response.abstained is True


def test_query_abstains_when_live_telemetry_is_requested(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query("What is the live vibration telemetry reading right now?")

    assert response.abstained is True
    assert response.citations == []
    assert response.confidence == 0.0
    assert "cannot access live equipment telemetry" in response.answer.lower()


def test_measurement_question_returns_measurements_not_only_causes(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query("What measurements should I take for an overheating motor?")

    assert response.abstained is False
    assert "measured current" in response.answer.lower()
    assert "phase-to-phase voltage" in response.answer.lower()


def test_restart_question_returns_items_to_monitor(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query("What should I monitor after restarting the motor?")

    assert response.abstained is False
    assert "monitor current, voltage, temperature, and vibration" in response.answer.lower()


def test_overgreasing_question_returns_temperature_effect(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query("Can too much grease make the bearing hot?")

    assert response.abstained is False
    assert "over-greasing can increase bearing temperature" in response.answer.lower()


def test_explanatory_unsupported_prompt_still_abstains(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    response = service.query(
        "Which hydraulic oil should I use? — should refuse because it is not in the manual."
    )

    assert response.abstained is True
    assert response.citations == []


def test_feedback_is_stored_as_jsonl(tmp_path: Path) -> None:
    service = build_service(tmp_path)

    service.store_feedback(
        {
            "question": "Why is the pump hot?",
            "answer": "Check ventilation.",
            "rating": "positive",
            "comment": None,
        }
    )

    stored = service.settings.feedback_path.read_text(encoding="utf-8")
    assert '"rating": "positive"' in stored


def test_multi_part_query_uses_diverse_evidence(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, chunk_size=18, chunk_overlap=3)
    settings.ensure_directories()
    (settings.raw_dir / "motor.md").write_text(
        "Motor overheating can result from restricted ventilation and overload. "
        "Inspect the cooling fan and measure current. "
        "Increased motor vibration can result from loose mounting bolts and shaft misalignment. "
        "Inspect the base and coupling alignment.",
        encoding="utf-8",
    )
    service = PlantOpsService(settings)
    service.initialize()

    response = service.query("What causes motor overheating and vibration?")

    assert response.abstained is False
    assert "overheating" in response.answer.lower()
    assert "vibration" in response.answer.lower()
    assert len({citation.chunk_id for citation in response.citations}) >= 2

