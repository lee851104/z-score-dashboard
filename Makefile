.PHONY: setup test lint check serve build

setup:
	uv sync --frozen

test:
	uv run --frozen pytest

lint:
	uv run --frozen ruff check .
	uv run --frozen ruff format --check .

check: lint test

serve:
	uv run --frozen python server.py

build:
	uv build
	uv run --frozen python scripts/check_wheel.py
