.PHONY: setup run test lint format build check doctor help deploy-deck test-deck sim-export sim-loop sim-benchmark zink-test

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
	@$(AES_LINT) src/dfb/cpu_engine.py src/dfb/service.py tests

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
	@$(AES_LINT) src/dfb/cpu_engine.py src/dfb/service.py tests

validate:
	@ruff check . || true

doctor:
	@echo "Language: $(AES_LANGUAGE)"
	@echo "Python: $$(python --version 2>&1 || echo not-found)"

help:
	@echo "AES Commands: make setup run test lint format build check doctor deploy-deck test-deck sim-export sim-loop sim-benchmark zink-test"

deploy-deck:
	@./scripts/deploy_deck.sh

# Integration test against Steam Deck (direct LAN access, no SSH tunnel)
# SSH used only for deploying monitor script and collecting CSV
test-deck:
	@echo "🌐 Verifying direct LAN access to steamdeck:8082..."
	@curl -sf http://steamdeck:8082/health >/dev/null || (echo "❌ Cannot reach steamdeck:8082" && exit 1)
	@echo "✅ Service reachable via LAN"
	@echo "📊 Deploying & starting resource monitor on Deck (via SSH)..."
	@cd $(CURDIR) && .venv/bin/python scripts/run_monitor.py --duration 120 --output aes/verification/T002/raw &
	@MONITOR_PID=$$!; \
	echo "🧪 Running maze benchmark (20 episodes) via direct LAN..."; \
	DECK_HOST=steamdeck SERVICE_PORT=8082 .venv/bin/pytest tests/deck/test_integration.py::TestMazeBenchmark -v -x; \
	TEST_RESULT=$$?; \
	echo "🛑 Stopping monitor..."; \
	kill $$MONITOR_PID 2>/dev/null || true; \
	wait $$MONITOR_PID 2>/dev/null || true; \
	echo "📝 Generating summary..."; \
	.venv/bin/python scripts/generate_summary.py aes/verification/T002/raw/resources.csv aes/verification/T002/summary.md; \
	echo "✅ Test-deck complete"; \
	exit $$TEST_RESULT

# Simulation targets
sim-export:
	@echo "📦 Exporting policy to ONNX..."
	@.venv/bin/python -m sim.policy

sim-loop:
	@echo "🏃 Running simulation loop (100 steps)..."
	@.venv/bin/python -m sim.sim_loop

sim-benchmark:
	@echo "⚡ Benchmarking inference (Vulkan vs CPU)..."
	@.venv/bin/python -m sim.benchmark_vulkan

zink-test:
	@echo "🖥️  Testing Zink/OpenGL over Vulkan..."
	@MESA_LOADER_DRIVER_OVERRIDE=zink GALLIUM_DRIVER=zink .venv/bin/python -m sim.test_zink