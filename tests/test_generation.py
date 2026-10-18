from app.domain import Chunk, SearchHit
from app.generation import GroundedLLMGenerator, INSUFFICIENT_EVIDENCE


class FakeProvider:
    name = "fake:test-model"

    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.system_prompt = ""
        self.user_prompt = ""

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def hit(chunk_id: str, text: str, score: float = 0.9) -> SearchHit:
    return SearchHit(
        chunk=Chunk(
            chunk_id=chunk_id,
            source="manual.md",
            page=1,
            text=text,
        ),
        score=score,
        lexical_score=score,
        vector_score=score,
        overlap_ratio=0.5,
    )


def test_grounded_generator_accepts_only_valid_citations() -> None:
    provider = FakeProvider("Check the cooling fan for blocked airflow [1].")
    generator = GroundedLLMGenerator(provider)
    evidence = [
        hit("overheat", "Blocked airflow can cause overheating."),
        hit("vibration", "Loose bolts can cause vibration."),
    ]

    result = generator.generate("Why is the motor hot?", evidence)

    assert result.generator == "fake:test-model"
    assert [item.chunk.chunk_id for item in result.cited_hits] == ["overheat"]
    assert "untrusted data" in provider.system_prompt
    assert "<evidence" in provider.user_prompt


def test_invalid_llm_citation_uses_safe_extractive_fallback() -> None:
    provider = FakeProvider("Replace the complete motor assembly [9].")
    generator = GroundedLLMGenerator(provider)
    evidence = [hit("overheat", "Blocked airflow can cause overheating.")]

    result = generator.generate("Why is the motor overheating?", evidence)

    assert "fallback: invalid-citations" in result.generator
    assert result.cited_hits[0].chunk.chunk_id == "overheat"
    assert "Replace the complete motor" not in result.answer


def test_llm_insufficient_evidence_abstains() -> None:
    provider = FakeProvider(INSUFFICIENT_EVIDENCE)
    generator = GroundedLLMGenerator(provider)

    result = generator.generate(
        "Which hydraulic oil should I use?",
        [hit("motor", "This manual describes motor ventilation.")],
    )

    assert result.cited_hits == []
    assert "enough evidence" in result.answer
    assert result.generator == "fake:test-model"


def test_provider_failure_uses_safe_extractive_fallback() -> None:
    provider = FakeProvider(RuntimeError("provider offline"))
    generator = GroundedLLMGenerator(provider)

    result = generator.generate(
        "Why is the motor overheating?",
        [hit("overheat", "Blocked airflow can cause overheating.")],
    )

    assert "fallback: RuntimeError" in result.generator
    assert result.cited_hits

