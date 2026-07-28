# Coligo Monorepo AI Assistant Guidelines (`ai_rules.md`)

> **Canonical file:** [`.agents/AGENTS.md`](.agents/AGENTS.md) has the full,
> up-to-date picture (verified repo state, gaps, Swagger testing workflow).
> This file is a short mirror for tools that only read `ai_rules.md` — keep
> it in sync with `.agents/AGENTS.md` rather than letting it drift.

This repository follows strict modular conventions for FastAPI and Python monorepo development.

## 📁 Repository Map

- **`api/`**: Main FastAPI backend service.
  - `api/main.py`: App entry point, OpenAPI specs, Swagger docs, middleware.
  - `api/core/`: Application settings via `Pydantic BaseSettings`.
  - `api/routers/`: Feature-based route modules (`health.py`, `v1/...`).
  - `api/schemas/`: Pydantic V2 Request & Response DTOs.
  - `api/services/`: Pure business logic layer.
  - `api/models/`: Database / ORM entities.
- **`app/`**: Module reserved for future application UI components.
- **`pyproject.toml`**: Single source of truth for tool settings (`ruff`, `mypy`, dependencies).
- **`Makefile`**: Developer task runner (`make setup`, `make lint`, `make format`, `make check`).

## 🛠️ Code Conventions

1. **Async & Typing**: Write `async` route handlers where applicable and use type hints for all parameters and return values.
2. **Pydantic Schemas**: Every route must specify an explicit `response_model` using a schema from `api/schemas/`.
3. **Swagger Specs**: Provide concise docstrings and `summary` descriptions on all route handlers to generate rich Swagger docs at `/docs`.
4. **Pre-commit Quality**: Run `make check` before committing code.
