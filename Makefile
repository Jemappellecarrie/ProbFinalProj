PYTHON ?= python3
NPM ?= npm

.PHONY: backend-install frontend-install bootstrap-demo backend-dev frontend-dev demo-generate test-backend lint-backend format-backend typecheck-frontend

backend-install:
	cd backend && $(PYTHON) -m pip install -e ".[dev]"

frontend-install:
	cd frontend && $(NPM) install

bootstrap-demo:
	$(PYTHON) scripts/bootstrap_demo_data.py

backend-dev:
	cd backend && $(PYTHON) -m uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000

frontend-dev:
	cd frontend && $(NPM) run dev -- --host 0.0.0.0 --port 5173

demo-generate:
	$(PYTHON) scripts/run_demo_generation.py

test-backend:
	cd backend && $(PYTHON) -m pytest

lint-backend:
	cd backend && $(PYTHON) -m ruff check app tests

format-backend:
	cd backend && $(PYTHON) -m ruff format app tests

typecheck-frontend:
	cd frontend && $(NPM) run typecheck
