# PlantOps Copilot

An evaluated, citation-first RAG assistant for industrial maintenance manuals. It ingests PDF, Markdown, and text documents; retrieves supporting passages; answers with traceable evidence; and abstains when the indexed corpus does not support a safe response.

## Results at a glance

| Signal | Current result | Scope |
|---|---:|---|
| Recall@5 | 1.000 | 11 versioned questions |
| Mean reciprocal rank | 1.000 | 8 answerable questions |
| Abstention accuracy | 1.000 | 8 answerable + 3 unsupported |
| Citation precision | 1.000 | Sentence-selected citations |
| Baseline p95 latency | 9.749 ms | Local evaluation, generation excluded |
| Automated tests | 27 | API, retrieval, generation, evaluation, deployment |

These numbers validate the pipeline on one synthetic motor manual split into three chunks. They are intentionally reported with their scope and are not presented as production-quality estimates.

## Core capabilities

- Hybrid retrieval with BM25 and deterministic hashing vectors
- Optional BGE semantic embeddings through FastEmbed/ONNX
- Query-aware reranking and safe evidence thresholds
- Extractive answers with page, chunk, excerpt, and score provenance
- Grounded LLM synthesis through Ollama or an OpenAI-compatible endpoint
- Citation-ID validation with automatic extractive fallback
- Safe abstention for out-of-corpus questions
- Evaluation using Recall@K, MRR, citation precision, abstention, and latency
- Responsive browser UI for document ingestion, chat, citations, feedback, and benchmark visibility
- FastAPI, CI, health checks, security headers, native Python deployment, and optional Docker packaging

## Architecture

```text
PDF / Markdown / text
          │
          ▼
 document loader ──► overlapping chunks ──► persisted JSON index
                                                   │
 question ──► BM25 ───────────────┐                │
              hashing or BGE ─────┼─► rerank ──────┘
                                  │
                                  ▼
                        evidence threshold
                         │               │
                    supported       unsupported
                         │               │
                         ▼               ▼
              extractive or grounded   abstain
                 LLM generation
                         │
                         ▼
            validated citations + confidence
                         │
                         ▼
                  FastAPI + web UI
```

The local extractive generator is the default, keeping the complete demo deterministic and usable without API credentials. Optional LLM output is accepted only when it cites valid retrieved evidence IDs.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m app.cli ingest
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) for the application or [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation.

Run the test suite:

```bash
pytest --cov=app --cov-report=term-missing
```

Run the versioned baseline evaluation:

```bash
python -m app.evaluation
```

## Semantic retrieval

Install the optional runtime and evaluate BGE vectors:

```bash
python -m pip install -r requirements-semantic.txt
PLANTOPS_EMBEDDING_BACKEND=fastembed python -m app.evaluation
PLANTOPS_EMBEDDING_BACKEND=fastembed uvicorn app.main:app --port 8001
```

The first semantic run downloads `BAAI/bge-small-en-v1.5` into `data/models`; later runs reuse the local cache. On the current small, terminology-heavy benchmark, semantic retrieval matches the baseline ranking and abstention metrics but has lower citation precision and higher latency. See [evaluation/results.md](evaluation/results.md) for the measured comparison and limitations.

## Grounded LLM generation

Use a local Ollama model:

```bash
ollama pull llama3.2:3b
PLANTOPS_GENERATOR=ollama uvicorn app.main:app --port 8001
```

Or use an OpenAI-compatible endpoint:

```bash
export PLANTOPS_GENERATOR=openai-compatible
export PLANTOPS_OPENAI_API_KEY='your-key'
export PLANTOPS_OPENAI_BASE_URL='https://api.openai.com'
export PLANTOPS_OPENAI_MODEL='gpt-4.1-mini'
uvicorn app.main:app --port 8001
```

Provider failures, missing citations, and invalid citation IDs trigger the extractive fallback. A provider response of `INSUFFICIENT_EVIDENCE` becomes a safe abstention.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Browser interface |
| `GET` | `/health` | Runtime, index, and upload status |
| `GET` | `/documents` | Indexed sources and chunk counts |
| `GET` | `/benchmark` | Versioned evaluation summary |
| `POST` | `/documents/ingest` | Reindex the corpus and optionally upload one document |
| `POST` | `/query` | Return a cited answer or safe abstention |
| `POST` | `/feedback` | Store positive or negative answer feedback |

Example query:

```bash
curl -s http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"What can cause the motor to overheat?"}'
```

## Deployment

The included Render Blueprint uses its native Python runtime, so Docker is not
required locally or in production:

```bash
pip install -r requirements.txt
python -m app.server
```

Push the repository to GitHub or GitLab, create a Render Blueprint from it, and
Render will run the configured build command, start command, and `/health`
check. Public uploads are disabled in that deployment.

Docker remains an optional, portable packaging path. Run locally with Docker
Compose when Docker is available:

```bash
docker compose up --build
```

The optional image runs as a non-root user, reads the hosting platform's `PORT`, exposes `/health`, and includes a container health check. CI builds and smoke-tests this image on GitHub-hosted runners, while `render.yaml` deploys the same application without Docker.

Deployment instructions and persistence tradeoffs are documented in [docs/deployment.md](docs/deployment.md).

## Configuration

Copy values from `.env.example` into your environment as needed.

| Variable | Default | Purpose |
|---|---|---|
| `PLANTOPS_DATA_DIR` | `./data` | Raw documents, index, uploads, feedback, and model cache |
| `PLANTOPS_EMBEDDING_BACKEND` | `hash` | `hash`, `fastembed`, or `sentence-transformers` |
| `PLANTOPS_GENERATOR` | `extractive` | `extractive`, `ollama`, or `openai-compatible` |
| `PLANTOPS_MIN_SCORE` | `0.20` | Minimum evidence score |
| `PLANTOPS_MAX_UPLOAD_BYTES` | `10000000` | Per-file upload limit |
| `PLANTOPS_ALLOW_UPLOADS` | `true` | Disable uploads for an unauthenticated public demo |

## Repository map

```text
app/                    FastAPI, retrieval, generation, and web UI
data/raw/               Synthetic demonstration manual
evaluation/             Versioned questions, benchmark summary, and analysis
tests/                  Unit and API tests
docs/deployment.md      Local and hosted deployment guide
render.yaml             Native Python Render Blueprint
Dockerfile              Optional non-root container image
```

## Safety and honest limitations

- The included maintenance manual is synthetic.
- The benchmark has only 11 questions and has not been independently reviewed.
- Text-based PDFs are supported; scanned PDFs need OCR.
- Citations prove retrieval provenance, not universal equipment safety.
- The app has no user authentication or malware scanning. Keep uploads disabled on a public demo.
- Local JSON storage is suitable for a single-instance demonstration, not concurrent multi-instance production.
- A real deployment should add authenticated object storage, a database or vector store, rate limiting, observability, and a larger held-out evaluation set.
