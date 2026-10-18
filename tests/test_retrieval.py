from app.domain import Chunk
from app.retrieval import HybridRetriever, tokenize


def test_tokenize_aligns_common_maintenance_word_forms() -> None:
    assert "overheat" in tokenize("overheating")
    assert tokenize("cause caused causes") == ["cause", "cause", "cause"]
    assert "measure" in tokenize("measurements measured")
    assert "monitor" in tokenize("monitoring monitored")
    assert "grease" in tokenize("over-greasing")
    assert tokenize("not in the manual") == []


def test_hybrid_scores_remain_calibrated_without_tie_saturation() -> None:
    chunks = [
        Chunk("relevant", "manual.md", 1, "Motor overheating can result from overload."),
        Chunk("incidental", "manual.md", 1, "Restart the motor after inspection."),
    ]
    hits = HybridRetriever(chunks).search("What causes the motor to overheat?", top_k=2)

    assert hits[0].chunk.chunk_id == "relevant"
    assert 0.0 <= hits[1].score < hits[0].score <= 1.0
