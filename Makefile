.PHONY: install install-semantic run test ingest evaluate evaluate-semantic

install:
	python -m pip install -r requirements-dev.txt

install-semantic:
	python -m pip install -r requirements-semantic.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest --cov=app --cov-report=term-missing

ingest:
	python -m app.cli ingest

evaluate:
	python -m app.evaluation

evaluate-semantic:
	PLANTOPS_EMBEDDING_BACKEND=fastembed python -m app.evaluation

