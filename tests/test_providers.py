import pytest

from app.providers import OllamaProvider, OpenAICompatibleProvider


class StubClient:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.url = ""
        self.payload: dict[str, object] = {}
        self.headers: dict[str, str] = {}

    def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        self.url = url
        self.payload = payload
        self.headers = headers or {}
        return self.response


def test_ollama_provider_extracts_message_content() -> None:
    client = StubClient({"message": {"content": "Check ventilation [1]."}})
    provider = OllamaProvider("http://localhost:11434/", "test-model", client)  # type: ignore[arg-type]

    answer = provider.complete("system", "question")

    assert answer == "Check ventilation [1]."
    assert client.url == "http://localhost:11434/api/chat"
    assert client.payload["stream"] is False


def test_openai_compatible_provider_sends_bearer_token() -> None:
    client = StubClient(
        {"choices": [{"message": {"content": "Inspect the fan [1]."}}]}
    )
    provider = OpenAICompatibleProvider(
        "https://example.test",
        "test-model",
        "secret-key",
        client,  # type: ignore[arg-type]
    )

    answer = provider.complete("system", "question")

    assert answer == "Inspect the fan [1]."
    assert client.url == "https://example.test/v1/chat/completions"
    assert client.headers["Authorization"] == "Bearer secret-key"


def test_openai_compatible_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="PLANTOPS_OPENAI_API_KEY"):
        OpenAICompatibleProvider(
            "https://example.test",
            "test-model",
            None,
            StubClient({}),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("response", "message"),
    [
        ({}, "Ollama response"),
        ({"choices": []}, "OpenAI-compatible response"),
    ],
)
def test_provider_rejects_malformed_responses(
    response: dict[str, object], message: str
) -> None:
    client = StubClient(response)
    if "Ollama" in message:
        provider = OllamaProvider("http://localhost", "model", client)  # type: ignore[arg-type]
    else:
        provider = OpenAICompatibleProvider(
            "https://example.test", "model", "key", client  # type: ignore[arg-type]
        )

    with pytest.raises(RuntimeError, match=message):
        provider.complete("system", "question")

