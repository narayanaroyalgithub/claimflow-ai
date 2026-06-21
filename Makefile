.PHONY: install dev test lint seed load

install:
	python -m pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check .

seed:
	python -m app.seed

load:
	python -m app.ingestion --zip "$${SYNTHEA_ZIP}"

