# Coligo Repository — Agent Guidelines

This is the canonical instruction file AI coding agents (Claude Code, Cursor,
Copilot, etc.) should read first. `ai_rules.md` at the repo root mirrors a
short version of this file for tools that only look there — if you edit one,
keep the other in sync or just point it back here.

## 1. What this repo actually is right now

Read this section before trusting the big narrative in `README.md`. The
README documents the **target product vision** for a SIH 2025 hackathon
project (DTE Rajasthan admissions chatbot: RAG over pgvector, WhatsApp
integration, Celery workers, Docker Compose, a React frontend, Railway
deploy). None of that exists in this repo yet.

What actually exists today, verified by running it:

- A minimal **FastAPI** backend under `api/` with health endpoints
  (`/health`, `/health/detailed`) and interactive docs correctly mounted at
  `/docs` (Swagger UI), `/redoc` (ReDoc), and `/openapi.json`.
- A WhatsApp Cloud API webhook **trigger** (`GET`/`POST /webhook` in
  `api/routers/whatsapp.py`): verification handshake, `X-Hub-Signature-256`
  verification, message extraction, and admin-vs-student routing — but it
  only logs the routing decision, it does **not send replies**. There's no
  `chat_service`/LLM to generate a reply with yet, and admin commands
  (`/ingest`, `/stats`, `/refresh`) are detected/logged but not executed.
- A pytest suite under `api/tests/` that exercises all of the above
  (`make test`).
- No database, no Redis, no Celery, no React frontend, no Docker, no CI
  workflow, and no `alembic/` — these are all future work tracked only as
  prose/ADRs in `README.md`.
- `app/` is an empty placeholder package reserved for a future
  frontend/UI app; it has no routes or components yet.

When asked to "add a feature," check first whether it's describing the
current MVP (`api/`) or the aspirational architecture in the README. Don't
silently scaffold pgvector/Celery/WhatsApp code unless the user asks for that
specific piece — the fastest way to make this repo worse is to half-build a
subsystem nobody asked for yet.

## 2. Folder structure & layering rules

```
coligo/
├── api/                     # The actual FastAPI backend (this is real)
│   ├── main.py              # App init, middleware, docs config, router mounts
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings, reads .env
│   │   ├── logging.py       # structlog setup — pino-equivalent structured logging
│   │   └── middleware.py    # RequestLoggingMiddleware — pino-http equivalent
│   ├── routers/              # One module per feature; mounted in main.py
│   │   ├── health.py
│   │   └── whatsapp.py       # GET/POST /webhook — Meta Cloud API trigger
│   ├── schemas/              # Pydantic v2 request/response DTOs
│   │   ├── health.py
│   │   └── whatsapp.py       # Meta webhook payload DTOs + flattened ParsedMessage
│   ├── services/              # Business logic layer
│   │   ├── health_service.py
│   │   └── whatsapp_service.py  # signature verify, extract_message, admin routing
│   ├── models/                 # DB/ORM entities (empty scaffold so far — no DB wired up yet)
│   └── tests/                   # pytest + FastAPI TestClient
├── app/                      # Reserved for a future frontend/UI app — empty today
├── .env.example              # Copy to .env; never commit .env
├── pyproject.toml            # Deps + tool config (ruff, mypy, pytest)
├── Makefile                  # make setup / lint / format / check / test / dev
└── .pre-commit-config.yaml   # ruff lint+format, whitespace/EOF/yaml/json checks
```

## 3. Coding & architectural standards

- **Python version**: >= 3.10 (repo's `.venv` currently runs 3.12).
- **Env manager**: this repo uses `uv`, not raw `pip` — the project `.venv`
  has no `pip` binary inside it by design. Install deps with
  `uv pip install --python .venv -e ".[dev]"` (this is what `make
  install-deps` runs). Don't `pip install` directly into `.venv`.
- **FastAPI handlers**: always use explicit type annotations and a Pydantic
  `response_model` on every route.
- **Routing**: keep `api/main.py` thin — only app setup, middleware, and
  `include_router()` calls. Route logic lives in `api/routers/<feature>.py`.
- **Schemas**: request/response models live in `api/schemas/`. Never return
  an ORM model directly from a route.
- **Config**: source all configuration from `api.core.settings`
  (`pydantic_settings.BaseSettings`, backed by `.env`). Never hardcode
  secrets, hosts, or ports in route/service code.
- **Formatting/linting**: `ruff format` (88-char lines) and `ruff check
  --fix`, enforced via pre-commit (`make check`).
- **Logging**: structured logging via `structlog`, configured once in
  `api/core/logging.py::configure_logging()` (called at import time in
  `api/main.py`). This is the Python equivalent of a pino setup — pretty
  colored console output in dev, single-line JSON when `ENVIRONMENT=production`.
  Every router and service gets its own scoped logger:
  `logger = get_logger(__name__)` at the top of the module (see
  `api/routers/health.py` and `api/services/health_service.py` for the
  pattern). Every HTTP request is also logged automatically by
  `RequestLoggingMiddleware` in `api/core/middleware.py` (method, path,
  status, duration) — the equivalent of Express's `pino-http`. There is no
  repository/DB layer yet to add logging to; when one is added, give it the
  same `get_logger(__name__)` treatment.

## 4. Running the API and testing it with Swagger

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
# or: make dev
```

Then open:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Raw OpenAPI schema: http://localhost:8000/openapi.json

This is generated automatically from the Pydantic schemas and route
docstrings/`summary=` fields in `api/routers/*.py` — there is no manual
OpenAPI YAML to keep in sync (see ADR-008 in `README.md`).

Automated verification lives in `api/tests/test_docs.py` (asserts `/docs`
and `/redoc` return 200 and that `/openapi.json` lists the expected paths)
and `api/tests/test_health.py` (asserts the health payloads). Run both with:

```bash
make test
# or directly: .venv/bin/python -m pytest -v
```

## 5. Developer workflow for adding a new endpoint

1. Define request/response Pydantic schemas in `api/schemas/<feature>.py`.
2. Put business logic in `api/services/<feature>.py` — routers should not
   contain logic beyond calling into services and shaping the response.
3. Create the route handler in `api/routers/<feature>.py` with a
   `response_model`, a `summary=`, and a docstring (this is what makes the
   Swagger docs actually useful).
4. Mount it in `api/main.py` via `app.include_router(...)`, and re-export it
   from `api/routers/__init__.py` the same way `health_router` is done.
5. Add a test in `api/tests/test_<feature>.py` using the `client` fixture
   from `api/tests/conftest.py`.
6. Run `make check && make test` before committing.

## 6. Known gaps (don't assume these are done just because README says so)

- `.env` is not created by default — copy `.env.example` first.
- No database/ORM wiring yet — `api/models/` is an empty package.
- No CI workflow file exists (`README.md`'s `.github/workflows/ci.yml` is
  aspirational, not present in `.github/` — there is no `.github/` here).
- No frontend exists under `app/` yet.
- WhatsApp webhook receives and routes events but **does not reply** —
  `whatsapp_service.send_text()` (an outbound Graph API call) doesn't exist
  yet; building it needs a `chat_service` to generate the reply content
  first. Admin commands are matched/logged in `whatsapp_service.py` but
  none of them actually run (`/ingest` needs S3 + Celery, `/stats` needs
  the analytics table, `/refresh` needs the RAG pipeline — none exist yet).
