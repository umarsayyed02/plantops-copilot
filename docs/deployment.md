# Deployment guide

PlantOps Copilot runs as a single Python web service. The browser UI and API are served from the same origin, so no separate frontend deployment or CORS configuration is required. Docker is optional.

## Local production-style run without Docker

```bash
source .venv/bin/activate
PLANTOPS_ALLOW_UPLOADS=false python -m app.server
```

Verify the service:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/benchmark
```

The server reads `PORT` dynamically, defaults to `8000`, initializes the sample
index during startup, and serves the API and browser interface together.

## Optional local Docker run

Build and run the baseline image:

```bash
docker build -t plantops-copilot .
docker run --rm -p 8000:8000 \
  -e PLANTOPS_ALLOW_UPLOADS=false \
  plantops-copilot
```

Verify the container:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/benchmark
```

The optional image:

- runs as the unprivileged `plantops` user;
- reads `PORT` dynamically, defaulting to `8000`;
- initializes the sample index during application startup;
- includes the UI, sample manual, and benchmark data;
- exposes a Docker health check;
- supports graceful termination through the Python/Uvicorn entry point.

## Render Blueprint deployment without Docker

The repository includes `render.yaml`, configured for a small public deployment in the Singapore region.

1. Push the repository to GitHub or GitLab.
2. In Render, create a new Blueprint and select the repository.
3. Review the proposed `plantops-copilot` web service.
4. Apply the Blueprint and wait for `/health` to pass.
5. Open the generated `onrender.com` URL and test one suggested question.

The Blueprint uses Render's native Python runtime with
`pip install -r requirements.txt` as its build command and
`python -m app.server` as its start command. It deploys after CI checks pass and deliberately uses:

- the offline hashing-vector baseline, avoiding model-download cold starts;
- the extractive generator, avoiding API keys and external inference costs;
- `PLANTOPS_ALLOW_UPLOADS=false`, preventing anonymous users from altering the shared demo corpus.

Render's Blueprint specification documents `runtime: python`, `buildCommand`, `startCommand`, `healthCheckPath`, and `autoDeployTrigger`: <https://render.com/docs/blueprint-spec>.

## Storage model

The free deployment uses ephemeral service storage. The bundled sample manual is committed with the application, while runtime feedback and generated index files can disappear during a redeploy or restart. This is acceptable for a read-only demonstration.

For persistent uploads, use a paid persistent disk or external object storage. If attaching a disk, mount it at a dedicated path such as `/var/data/plantops`, set `PLANTOPS_DATA_DIR` to that path, seed the raw corpus separately, and enable uploads only after adding authentication and file scanning.

## Pre-deployment checklist

- Run `pytest --cov=app --cov-report=term-missing`.
- Run `python -m app.evaluation` and review regressions.
- Confirm the native Python build and start commands work from a clean environment.
- Keep uploads disabled for anonymous traffic.
- Do not commit `.env` files or API keys.
- Confirm `/health`, `/benchmark`, one supported question, and one unsupported question.
- Add rate limiting and structured logs before marketing the service as production-ready.
- Use a real database/vector store before running multiple service instances.

## Optional Docker packaging

The repository retains a non-root Dockerfile. GitHub Actions builds it and
smoke-tests `/health`, so a local Docker installation is not required to keep
the container path checked. To use semantic dependencies in that image:

The Dockerfile supports semantic dependencies through a build argument:

```bash
docker build \
  --build-arg INSTALL_SEMANTIC=true \
  -t plantops-copilot:semantic .
```

Run it with:

```bash
docker run --rm -p 8000:8000 \
  -e PLANTOPS_EMBEDDING_BACKEND=fastembed \
  -e PLANTOPS_ALLOW_UPLOADS=false \
  plantops-copilot:semantic
```

The first startup downloads the configured BGE model unless a cached model directory is mounted. The baseline image is faster and more predictable when semantic retrieval is not required.
