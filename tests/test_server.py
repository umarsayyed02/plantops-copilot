import pytest

from app.server import server_port


def test_server_port_uses_platform_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "9123")
    assert server_port() == 9123


def test_server_port_rejects_invalid_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "70000")
    with pytest.raises(ValueError, match="between 1 and 65535"):
        server_port()
