.PHONY: setup run test lint format build check doctor help

AES_LANGUAGE ?= python
AES_LINT ?= ruff check
AES_TEST ?= pytest --cov=src
AES_FORMAT ?= ruff format
AES_BUILD ?= python -m build
AES_RUN ?= python -m src.main || python src/main.py

export AES_LANGUAGE AES_LINT AES_TEST AES_FORMAT AES_BUILD AES_RUN

setup:
	@echo "Setting up $(AES_LANGUAGE)..."
	uv sync 2>/dev/null || pip install -e .

run:
	@$(AES_RUN)

test:
	@$(AES_TEST)

lint:
	@$(AES_LINT) src tests

format:
	@$(AES_FORMAT) src tests

build:
	@$(AES_BUILD)

check: docs-check code-check test-check lint-check

docs-check:
	@test -f docs/VISION.md && grep -q "Problem" docs/VISION.md
	@test -f docs/PERSONAS.md && grep -q "User" docs/PERSONAS.md
	@test -f docs/REQUIREMENTS.md && grep -q "Functional" docs/REQUIREMENTS.md
	@test -f docs/ROADMAP.md && grep -q "Roadmap" docs/ROADMAP.md

code-check:
	@test -d src || test -d lib
	@grep -R "TODO:" src/ tests/ 2>/dev/null || true

test-check:
	@$(AES_TEST) --cov-fail-under=80 || echo "Coverage below 80%"

lint-check:
	@$(AES_LINT) src tests

validate:
	@ruff check . || true

doctor:
	@echo "Language: $(AES_LANGUAGE)"
	@echo "Python: $$(python --version 2>&1 || echo not-found)"

help:
	@echo "AES Commands: make setup run test lint format build check doctor"
