from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class CompletionProvider(Protocol):
    name: str

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass(frozen=True)
class HTTPJSONClient:
    timeout_seconds: float = 30.0

    def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        encoded = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=encoded,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"LLM provider returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach LLM provider: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("LLM provider request timed out") from exc

        value = json.loads(body)
        if not isinstance(value, dict):
            raise RuntimeError("LLM provider returned an unexpected response")
        return value


class OllamaProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        client: HTTPJSONClient,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = client
        self.name = f"ollama:{model}"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0},
        }
        response = self.client.post(f"{self.base_url}/api/chat", payload)
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise RuntimeError("Ollama response did not contain message.content")
        return str(message["content"]).strip()


class OpenAICompatibleProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None,
        client: HTTPJSONClient,
    ) -> None:
        if not api_key:
            raise ValueError(
                "PLANTOPS_OPENAI_API_KEY is required for the openai-compatible generator"
            )
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.client = client
        self.name = f"openai-compatible:{model}"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = self.client.post(
            f"{self.base_url}/v1/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenAI-compatible response did not contain choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise RuntimeError("OpenAI-compatible response choice was invalid")
        message = first.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise RuntimeError(
                "OpenAI-compatible response did not contain message.content"
            )
        return str(message["content"]).strip()

