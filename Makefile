.PHONY: help install install-dev test lint format check clean run

help:
	@echo "Spectra App - Development Commands"
	@echo "===================================="
	@echo "install       Install production dependencies"
	@echo "install-dev   Install dev dependencies (linters, formatters)"
	@echo "test          Run test suite"
	@echo "lint          Run linters (pylint, flake8, mypy)"
	@echo "format        Format code (black, isort)"
	@echo "check         Run format check without modifying files"
	@echo "clean         Remove cache and temporary files"
	@echo "run           Launch the application"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v

lint:
	@echo "Running pylint..."
	-pylint app/
	@echo "\nRunning flake8..."
	-flake8 app/ tests/
	@echo "\nRunning mypy..."
	-mypy app/

format:
	@echo "Running black..."
	black app/ tests/
	@echo "Running isort..."
	isort app/ tests/

check:
	@echo "Checking format with black..."
	black --check app/ tests/
	@echo "Checking imports with isort..."
	isort --check-only app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f tmpclaude-*

run:
	python -m app.main
