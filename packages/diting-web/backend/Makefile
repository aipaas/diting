.PHONY: help install dev test lint format run migrate init-db clean

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  dev          - Install dev dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linter"
	@echo "  format       - Format code"
	@echo "  run          - Run the application"
	@echo "  migrate      - Run database migrations"
	@echo "  init-db      - Initialize database (admin user + metrics)"
	@echo "  worker       - Run ARQ worker"
	@echo "  clean        - Clean generated files"

install:
	uv sync

dev:
	uv sync --all-extras

test:
	pytest

lint:
	ruff check .
	mypy src/

format:
	ruff format .
	ruff check --fix .

run:
	python -m diting_web.main

migrate:
	alembic upgrade head

init-db: migrate
	python -m diting_web.scripts.init_admin
	python -m diting_web.scripts.init_metrics

worker:
	python -m diting_web.workers.worker

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage

