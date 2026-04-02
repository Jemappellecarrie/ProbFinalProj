PYTHON ?= python3
BACKEND_VENV ?= backend/.venv
BACKEND_PYTHON ?= $(BACKEND_VENV)/bin/python
NPM ?= npm
RELEASE_SMOKE_DIR ?= data/processed/release_validation/make_release_check
PYTHON_CHECK_PATHS ?= backend/app/services/evaluation_service.py backend/tests scripts

.PHONY: backend-venv backend-install frontend-install bootstrap bootstrap-demo backend-dev frontend-dev demo-generate evaluate-batch evaluate-batch-smoke release-summary test-backend lint-backend format-backend format-check-backend typecheck-frontend frontend-build release-check

backend-venv:
	cd backend && $(PYTHON) -m venv .venv
	$(BACKEND_PYTHON) -m pip install --upgrade pip
	$(BACKEND_PYTHON) -m pip install -e ".[dev]"

backend-install:
	cd backend && $(PYTHON) -m pip install -e ".[dev]"

frontend-install:
	cd frontend && $(NPM) install

bootstrap: backend-venv frontend-install bootstrap-demo

bootstrap-demo:
	$(BACKEND_PYTHON) scripts/bootstrap_demo_data.py

backend-dev:
	cd backend && $(BACKEND_PYTHON) -m uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && $(NPM) run dev -- --host 0.0.0.0 --port 5173

demo-generate:
	$(BACKEND_PYTHON) scripts/run_demo_generation.py

evaluate-batch:
	$(BACKEND_PYTHON) scripts/evaluate_batch.py --num-puzzles 10 --top-k 5

evaluate-batch-smoke:
	CONNECTIONS_DEMO_MODE=false $(BACKEND_PYTHON) scripts/evaluate_batch.py --num-puzzles 2 --top-k 1 --output-dir $(RELEASE_SMOKE_DIR) --no-traces --no-demo-mode

release-summary:
	$(BACKEND_PYTHON) scripts/build_release_summary.py --run-dir $(RELEASE_SMOKE_DIR)

test-backend:
	$(BACKEND_PYTHON) -m pytest backend/tests -q

lint-backend:
	$(BACKEND_PYTHON) -m ruff check $(PYTHON_CHECK_PATHS)

format-backend:
	$(BACKEND_PYTHON) -m ruff format $(PYTHON_CHECK_PATHS)

format-check-backend:
	$(BACKEND_PYTHON) -m ruff format --check $(PYTHON_CHECK_PATHS)

typecheck-frontend:
	cd frontend && $(NPM) run typecheck

frontend-build:
	cd frontend && $(NPM) run build

release-check:
	$(BACKEND_PYTHON) scripts/release_check.py --backend-python $(BACKEND_PYTHON) --output-dir $(RELEASE_SMOKE_DIR)
