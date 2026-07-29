# Coligo Repository — Agent Guidelines

This is the canonical instruction file AI coding agents (Claude Code, Cursor,
Copilot, etc.) should read first. `ai_rules.md` at the repo root mirrors a
short version of this file for tools that only look there — if you edit one,
keep the other in sync or just point it back here.

## 1. What this repo actually is right now

This project is a **TNEA (Tamil Nadu Engineering Admissions) counselling
assistant** — not Rajasthan/DTE. It answers student questions about TNEA
counselling and Tamil Nadu engineering college admissions over WhatsApp,
grounded in official college documents. The seed knowledge base covers Sri
Krishna College of Engineering and Technology (SKCET), Coimbatore
(`data/skcet_tnea_knowledge_base.pdf`). Keep the domain language (TNEA,
cutoff marks out of 200, communities OC/BC/BCM/MBC/SC/SCA/ST) consistent
in prompts, docs and sample data.

Read this section before trusting the big narrative in `README.md` — it
documents the **target product vision** (Celery workers, React frontend,
Railway deploy, escalation/analytics), much of which does not exist yet.

What actually exists today, verified by running it:

- A minimal **FastAPI** backend under `api/` with health endpoints
  (`/health`, `/health/detailed`) and interactive docs correctly mounted at
  `/docs` (Swagger UI), `/redoc` (ReDoc), and `/openapi.json`.
- A **WhatsApp Cloud API** integration (`api/routers/whatsapp.py` +
  `api/services/whatsapp_service.py`): `GET /webhook` verification
  handshake, `POST /webhook` with `X-Hub-Signature-256` verification,
  message extraction, admin-vs-student routing, and outbound replies via
  `send_text()`. Student text messages run the RAG pipeline and get a real
  answer sent back. Admin commands (`/ingest`, `/stats`, `/refresh`) are
  detected/logged but **not executed** — they need ingest/analytics
  services that don't exist yet.
- **Document ingestion** (`POST /documents/process`): PDF → text → chunks →
  Gemini embeddings → pgvector, with SHA-256 chunk deduplication.
- **RAG chat** (`POST /chat` and the WhatsApp path): embed query →
  pgvector cosine search → Gemini generation, returning answer + sources.
- **Conversation memory** (`api/services/conversation_service.py`,
  `api/models/conversation.py`): multi-turn chats keyed by a namespaced
  `session_key` — `whatsapp:<phone>` (automatic) or `web:<session_id>` (only
  when `/chat` is given a `session_id`; without one it stays stateless).
  Threads expire after `CONVERSATION_TTL_HOURS` (24); the last
  `CONVERSATION_MAX_TURNS` (6) reach the prompt. Crucially,
  `api/services/query_rewriter.py` condenses follow-ups ("what about ECE?")
  into standalone questions **before embedding** — without that step
  retrieval matches on the bare phrase and returns the wrong chunks. The
  condensed text is used only for retrieval; the user's original wording goes
  to the answering prompt. History is best-effort: any failure loading,
  saving, or rewriting is logged and the pipeline answers statelessly.
- **PostgreSQL + pgvector** via `docker-compose.yml`. In development the
  `vector` extension and all tables are created automatically at startup
  (`api/main.py` lifespan) — there is no Alembic migration setup.
- **No test suite** — tests were intentionally removed from this project.
  Verify changes by running the stack and exercising endpoints (see §4).
- No Redis, no Celery, no React frontend, no CI workflow, and no
  `alembic/` — these remain future work tracked as prose/ADRs in
  `README.md`.
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
│   ├── main.py              # App init, middleware, docs, router mounts, DB bootstrap
│   ├── core/
│   │   ├── config.py        # Settings via pydantic-settings, reads .env
│   │   ├── database.py      # Async SQLAlchemy engine/session + get_db dependency
│   │   ├── exceptions.py    # Document processing exception hierarchy
│   │   ├── logging.py       # structlog setup — pino-equivalent structured logging
│   │   └── middleware.py    # RequestLoggingMiddleware — pino-http equivalent
│   ├── routers/              # One module per feature; mounted in main.py
│   │   ├── health.py
│   │   ├── document.py       # POST /documents/process — PDF ingestion
│   │   ├── chat.py           # POST /chat — RAG query over HTTP
│   │   └── whatsapp.py       # GET/POST /webhook — Meta Cloud API
│   ├── schemas/              # Pydantic v2 request/response DTOs
│   ├── services/              # Business logic layer
│   │   ├── health_service.py
│   │   ├── pdf_extractor.py     # PDF bytes -> text (pypdf)
│   │   ├── chunker.py           # text -> overlapping chunks + SHA-256
│   │   ├── embedding_service.py # Gemini batchEmbedContents (768-dim)
│   │   ├── document_service.py  # fetch -> extract -> chunk -> embed -> store
│   │   ├── llm_service.py       # Gemini generateContent
│   │   ├── rag_service.py       # embed query -> pgvector search -> LLM answer
│   │   ├── conversation_service.py # session threads, recent turns, history
│   │   ├── query_rewriter.py    # condense follow-ups into standalone questions
│   │   └── whatsapp_service.py  # signature verify, parse, routing, send_text
│   └── models/                 # SQLAlchemy ORM: Document/DocumentChunk (pgvector),
│                               #   Conversation/ConversationMessage (chat memory)
├── app/                      # Reserved for a future frontend/UI app — empty today
├── docker-compose.yml        # postgres (pgvector) + api
├── Dockerfile                # API image
├── .env.example              # Copy to .env; never commit .env
├── pyproject.toml            # Deps + tool config (ruff, mypy)
├── Makefile                  # make setup / lint / format / check / dev
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

## 4. Running and verifying the stack

The API needs PostgreSQL+pgvector. Either run everything in Docker:

```bash
docker compose up -d          # postgres + api
docker compose logs -f api
```

...or run just the database in Docker and the API on the host:

```bash
docker compose up -d postgres
make dev                      # uvicorn --reload on :8000
```

Then open:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Raw OpenAPI schema: http://localhost:8000/openapi.json

The spec is generated automatically from the Pydantic schemas and route
docstrings/`summary=` fields in `api/routers/*.py` — there is no manual
OpenAPI YAML to keep in sync (see ADR-008 in `README.md`).

**There is no test suite** — it was intentionally removed. Verify changes
by running the stack and exercising the real endpoints (see README's
"Testing the full flow"), and inspect stored data directly:

```bash
docker exec coligo_postgres psql -U dte -d dte_chatbot \
  -c "SELECT id, document_id, chunk_index, vector_dims(embedding) FROM document_chunks;"
```

Always run `make check` (ruff lint+format via pre-commit) and
`.venv/bin/mypy api/` before committing.

## 5. Developer workflow for adding a new endpoint

1. Define request/response Pydantic schemas in `api/schemas/<feature>.py`.
2. Put business logic in `api/services/<feature>.py` — routers should not
   contain logic beyond calling into services and shaping the response.
3. Create the route handler in `api/routers/<feature>.py` with a
   `response_model`, a `summary=`, and a docstring (this is what makes the
   Swagger docs actually useful).
4. Mount it in `api/main.py` via `app.include_router(...)`, and re-export it
   from `api/routers/__init__.py` the same way `health_router` is done.
5. If it touches the database, take `db: AsyncSession = Depends(get_db)`
   from `api/core/database.py` rather than creating a session yourself.
6. Run `make check` and `.venv/bin/mypy api/`, then exercise the endpoint
   against the running stack before committing.

## 6. Known gaps (don't assume these are done just because README says so)

- `.env` is not created by default — copy `.env.example` first and fill in
  `GEMINI_API_KEY` plus the `WHATSAPP_*` values. Without `GEMINI_API_KEY`
  both ingestion and chat fail (embedding/LLM calls raise).
- No CI workflow file exists (`README.md`'s `.github/workflows/ci.yml` is
  aspirational, not present in `.github/` — there is no `.github/` here).
- No frontend exists under `app/` yet.
- No Alembic migrations — tables are created at startup via
  `Base.metadata.create_all` and **only when `ENVIRONMENT=development`**.
  A production deploy currently has no schema-creation path.
- Admin commands are matched/logged in `whatsapp_service.py` but none of
  them actually run (`/ingest` needs S3 + Celery, `/stats` needs an
  analytics table, `/refresh` needs a reindex path — none exist yet).
- `document_service.process_document` dedupes chunks **globally** by
  SHA-256. If two different `document_ref`s have identical content, the
  second document row is created with **zero chunks**, so it can never be
  retrieved or cited as a source. Deleting the first document cascade-
  deletes the shared chunks, leaving both effectively empty.
- The webhook replies synchronously: the RAG round-trip (2 Gemini calls +
  a Graph API send) runs before Meta gets its 200, taking ~4s in practice.
  Meta's webhook timeout is short, so slow queries risk retries and
  duplicate replies. Moving the reply to a background task is the fix.
