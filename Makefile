.PHONY: all lint format check fix test

all: check test

lint:
	uv run ruff check .

fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

check:
	uv run ruff check . && uv run ruff format --check .

build-test-db:
	docker build -t pgvector-postgis -f Dockerfile.db .

test: build-test-db
	uv run pytest -x -s
