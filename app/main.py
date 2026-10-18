from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT, Settings
from app.schemas import (
    BenchmarkResponse,
    DocumentSummary,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)
from app.service import PlantOpsService


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    service = PlantOpsService(resolved_settings)
    static_dir = Path(__file__).resolve().parent / "static"
    benchmark_path = PROJECT_ROOT / "evaluation" / "benchmark.json"

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        service.initialize()
        yield

    application = FastAPI(
        title="PlantOps Copilot",
        version="0.1.0",
        description="Citation-first retrieval for industrial maintenance documents.",
        lifespan=lifespan,
    )
    application.state.service = service
    application.mount("/static", StaticFiles(directory=static_dir), name="static")

    @application.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net; connect-src 'self'"
        )
        return response

    @application.get("/", include_in_schema=False)
    def interface() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            chunks=len(service.chunks),
            generator=service.generator.name,
            embedding_backend=service.retriever.embedding_backend,
            uploads_enabled=resolved_settings.allow_uploads,
        )

    @application.get("/documents", response_model=list[DocumentSummary])
    def documents() -> list[DocumentSummary]:
        return service.document_summaries()

    @application.get("/benchmark", response_model=BenchmarkResponse)
    def benchmark() -> BenchmarkResponse:
        return BenchmarkResponse.model_validate_json(
            benchmark_path.read_text(encoding="utf-8")
        )

    @application.post("/documents/ingest", response_model=IngestResponse)
    async def ingest(file: UploadFile | None = File(default=None)) -> IngestResponse:
        try:
            if file is not None:
                if not resolved_settings.allow_uploads:
                    raise HTTPException(
                        status_code=403,
                        detail="Document uploads are disabled for this deployment.",
                    )
                content = await file.read(resolved_settings.max_upload_bytes + 1)
                if len(content) > resolved_settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File is too large. Maximum upload size is "
                            f"{resolved_settings.max_upload_bytes} bytes."
                        ),
                    )
                service.store_upload(file.filename or "upload.txt", content)
            document_count, chunk_count, sources = service.ingest_all()
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return IngestResponse(
            documents=document_count, chunks=chunk_count, sources=sources
        )

    @application.post("/query", response_model=QueryResponse)
    def query(payload: QueryRequest) -> QueryResponse:
        return service.query(payload.question, payload.top_k)

    @application.post("/feedback", response_model=FeedbackResponse)
    def feedback(payload: FeedbackRequest) -> FeedbackResponse:
        service.store_feedback(payload.model_dump())
        return FeedbackResponse(stored=True)

    return application


app = create_app()

