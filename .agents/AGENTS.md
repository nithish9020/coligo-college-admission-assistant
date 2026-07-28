# Coligo Repository AI Rules & Guidelines

## 1. Project Architecture & Overview
This repository is a **Python Monorepo** managed with `uv`, `pre-commit`, `ruff`, and `FastAPI`.

### Folder Structure & Layering Rules
```
coligo/
├── api/                   # Backend FastAPI Service
│   ├── main.py            # FastAPI initialization, middleware & router mounts
│   ├── core/              # Global configuration & environment settings (Pydantic BaseSettings)
│   ├── routers/           # API endpoints grouped by feature/version
│   ├── schemas/           # Pydantic v2 data validation schemas (Request/Response models)
│   ├── services/          # Business logic, LLM/RAG integration, database calls
│   └── models/            # Database / ORM models (SQLAlchemy/SQLModel)
├── app/                   # Reserved for future frontend/UI apps
├── pyproject.toml         # Central tool configurations (Ruff, Black, Mypy,Dependencies)
├── Makefile               # Task runner (`make setup`, `make lint`, `make format`, `make check`)
└── .pre-commit-config.yaml # Git pre-commit hooks (Ruff linter & formatter)
```

## 2. Coding & Architectural Standards

### Python & FastAPI Guidelines
- **Python Version**: Python >= 3.10 (3.12 recommended).
- **FastAPI Handlers**: Always use explicit type annotations and Pydantic `response_model` on router endpoints.
- **Routing**: Keep `api/main.py` clean. Place route handlers inside `api/routers/<feature>.py` and include them via `app.include_router()`.
- **Schemas**: Separate Request and Response models in `api/schemas/`. Do not pass ORM models directly to responses.
- **Configuration**: Always source configuration from `api.core.settings` using `Pydantic BaseSettings`. Never hardcode secrets or ports.

### Code Style & Quality Enforcement
- **Formatting**: Code formatting is enforced via `ruff format` (88 character line length).
- **Linting**: Linters run via `ruff check --fix`. Imports must be sorted automatically via `isort`/Ruff.
- **Pre-commit**: All commits MUST pass `make check` (`pre-commit run --all-files`).

## 3. Developer & AI Assistant Workflow
- **Adding new API Endpoints**:
  1. Define response/request Pydantic schemas in `api/schemas/`.
  2. Create business logic in `api/services/`.
  3. Create route handler in `api/routers/` and mount it in `api/main.py`.
- **Running Local Dev Server**:
  ```bash
  source .venv/bin/activate
  uvicorn api.main:app --reload --port 8000
  ```
- **Interactive Swagger Docs**: Available locally at `http://localhost:8000/docs`.
