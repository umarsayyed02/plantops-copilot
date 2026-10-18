from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_and_query_endpoints(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, chunk_size=50, chunk_overlap=5)
    settings.ensure_directories()
    (settings.raw_dir / "manual.txt").write_text(
        "Motor overheating may be caused by blocked ventilation. "
        "Disconnect power before cleaning the cooling fan.",
        encoding="utf-8",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        health = client.get("/health")
        interface = client.get("/")
        stylesheet = client.get("/static/styles.css")
        benchmark = client.get("/benchmark")
        response = client.post("/query", json={"question": "Why is the motor overheating?"})

    assert health.status_code == 200
    assert health.json()["chunks"] == 1
    assert health.json()["uploads_enabled"] is True
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert interface.status_code == 200
    assert "PlantOps Copilot" in interface.text
    assert stylesheet.status_code == 200
    assert "--signal" in stylesheet.text
    assert benchmark.status_code == 200
    assert len(benchmark.json()["results"]) == 2
    assert response.status_code == 200
    assert response.json()["abstained"] is False
    assert response.json()["citations"][0]["source"] == "manual.txt"


def test_upload_rejects_files_above_configured_limit(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, max_upload_bytes=4)
    app = create_app(settings)

    with TestClient(app) as client:
        response = client.post(
            "/documents/ingest",
            files={"file": ("manual.txt", b"12345", "text/plain")},
        )

    assert response.status_code == 413
    assert "Maximum upload size is 4 bytes" in response.json()["detail"]


def test_upload_can_be_disabled_for_public_deployments(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, allow_uploads=False)
    app = create_app(settings)

    with TestClient(app) as client:
        health = client.get("/health")
        response = client.post(
            "/documents/ingest",
            files={"file": ("manual.txt", b"safe text", "text/plain")},
        )

    assert health.json()["uploads_enabled"] is False
    assert response.status_code == 403
    assert not (settings.upload_dir / "manual.txt").exists()

