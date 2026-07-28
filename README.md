# DTE AI Chatbot — SIH 2025 (Problem Statement 1631)

> AI-powered student assistance chatbot for the Department of Technical Education, Government of Rajasthan. Centralized 24/7 virtual assistant handling admission queries, fee structures, cutoff predictions, scholarship info, and college data across hundreds of engineering and polytechnic institutes.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture Decisions (ADR)](#architecture-decisions-adr)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Core Flows](#core-flows)
- [WhatsApp Integration](#whatsapp-integration)
- [RAG Pipeline](#rag-pipeline)
- [Escalation Logic](#escalation-logic)
- [Environment Variables](#environment-variables)
- [Local Development Setup](#local-development-setup)
- [Docker Setup](#docker-setup)
- [CI/CD Pipeline](#cicd-pipeline)
- [API Reference](#api-reference)
- [Team & Task Management](#team--task-management)
- [Production Checklist](#production-checklist)

---

## Project Overview

**Problem:** During admission season, DTE Rajasthan receives thousands of identical queries from students, parents, and other stakeholders — about admissions, fees, cutoffs, scholarships, hostel availability, and placements. Colleges handle this manually via phone, email, and walk-ins, consuming significant staff time.

**Solution:** Centralized AI chatbot deployed across WhatsApp, web widget, and voice IVR. Uses Retrieval-Augmented Generation (RAG) over a vector database of DTE college data to answer queries accurately, in both English and Hindi, 24/7.

**Key differentiators over a generic FAQ bot:**
- Cutoff predictor — given a JEE rank + category, returns ranked college + branch recommendations based on 3 years of REAP allotment data
- Hindi/Hinglish native handling — no separate NLP pipeline, LLM handles it natively
- Two-attempt escalation with human handoff — confidence-scored, not binary fail/pass
- Admin CMS — DTE officers update data without touching code
- Analytics dashboard — query heatmap by district, escalation patterns, low-confidence clusters

---

## Architecture Decisions (ADR)

Every non-trivial decision is logged here. Written before building, not after.

### ADR-001 — FastAPI over Express.js for backend

**Decision:** Python + FastAPI
**Rejected:** Node.js + Express (team's primary stack)
**Reason:** LLM SDKs, embedding libraries (sentence-transformers), and pgvector clients are Python-first. FastAPI generates OpenAPI spec automatically from Pydantic models — no separate YAML file needed. For a project that will extend into more AI toolcalling over time, staying in the Python AI ecosystem reduces friction at every future decision point.
**Trade-off:** Team needs 2–3 days to adapt from Express mental model. Acceptable cost.

---

### ADR-002 — pgvector over Qdrant / Pinecone for vector storage

**Decision:** PostgreSQL + pgvector extension
**Rejected:** Qdrant, Pinecone, Weaviate
**Reason:** Team already runs PostgreSQL for structured data (fees, seats, cutoffs). Adding pgvector is one `CREATE EXTENSION` command. Reduces infrastructure from two databases to one. For SIH prototype scale, pgvector's performance is more than sufficient. Eliminates one Docker container, one connection pool, one set of credentials.
**Trade-off:** pgvector is slower than purpose-built vector DBs at >10M vectors. Not relevant at this scale.

---

### ADR-003 — DeepSeek V4 Flash as primary LLM

**Decision:** DeepSeek V4 Flash via `platform.deepseek.com`
**Rejected:** Anthropic Claude, OpenAI GPT-4o, Gemini
**Reason:** Lowest cost per token among frontier-class models (~$0.14/M input). New account gets 5M free tokens on signup — sufficient for full SIH development and demo. OpenAI-compatible API means zero code change if we switch providers later.
**Fallback:** Groq (Llama 3.1 70B) — free tier, fastest inference, wired as secondary provider in a try/except block.
**Trade-off:** DeepSeek occasionally freezes new signups and top-ups during high-traffic periods. Mitigated by Groq fallback.

---

### ADR-004 — Gemini text-embedding-004 for embeddings (not DeepSeek)

**Decision:** Google `text-embedding-004` via AI Studio
**Rejected:** DeepSeek embeddings, OpenAI text-embedding-3-small
**Reason:** Google AI Studio's embedding model is unlimited and free — no quota, no billing. LLM and embedding model are decoupled concerns; using the cheapest option per concern is correct. 768-dimension vectors work natively with pgvector.
**Trade-off:** Adds a second API provider to manage. Acceptable — embeddings are fire-and-forget.

---

### ADR-005 — WhatsApp Cloud API (Meta direct) for messaging

**Decision:** Meta WhatsApp Cloud API directly (no BSP like Twilio/360dialog)
**Rejected:** Twilio WhatsApp, 360dialog, Wati
**Reason:** No BSP markup on message costs. Direct API access. First 1,000 service conversations per month are free — sufficient for SIH development and demo. BSPs add a platform fee layer that is unnecessary for this scope.
**Trade-off:** No BSP support layer. Team owns webhook setup and error handling fully.

---

### ADR-006 — Single WhatsApp number with phone-number-based admin routing

**Decision:** One WhatsApp Business number, admin access controlled by sender phone number whitelist
**Rejected:** Two separate numbers (one for admin, one for students)
**Reason:** Since October 2025, Meta applies limits per Business Portfolio, not per number — two numbers share the same quota. Single number is simpler. Admin vs student routing is handled in the webhook handler by checking `message.from` against `ADMIN_NUMBERS` in env.
**Trade-off:** If an admin number is compromised, attacker can trigger document ingestion. Mitigated by requiring a `/ingest` command prefix, not triggering on raw document receipt.

---

### ADR-007 — No authentication layer on WhatsApp for students

**Decision:** Phone number = identity for students. No login, no OTP, no session.
**Rejected:** Username/password over WhatsApp, JWT sessions
**Reason:** WhatsApp is not an auth channel. Students asking admission questions don't need to be authenticated — the information is public. Phone number provides sufficient identity for analytics and session continuity. Adding auth would increase friction and reduce adoption.
**Trade-off:** No personalization beyond what the student provides in-conversation (rank, category, etc.).

---

### ADR-008 — FastAPI auto-generated OpenAPI (no manual YAML)

**Decision:** Pydantic models + FastAPI decorators define the spec
**Rejected:** Manual OpenAPI YAML-first (as used in the team's Express projects)
**Reason:** FastAPI generates a live OpenAPI spec at `/docs` and `/openapi.json` from Python type hints. Writing YAML manually on top of this would be duplication. The spec is always in sync with the implementation — no drift possible.
**Trade-off:** Less control over spec structure compared to manual YAML. Not a concern at this scale.

---

### ADR-009 — Langfuse for LLM observability

**Decision:** Langfuse (self-hosted or cloud free tier)
**Rejected:** No observability, custom logging only
**Reason:** Every LLM call must be traced: prompt version, retrieved chunks, latency, token count, cost, model used. Without this, debugging a bad answer is impossible. Langfuse's free cloud tier is sufficient; can self-host on the same Docker Compose stack if needed.
**Trade-off:** One more service to configure. Worth it — blind LLM systems are unmaintainable.

---

### ADR-010 — Railway for deployment (staging + production)

**Decision:** Railway
**Rejected:** AWS EC2, Render, Fly.io
**Reason:** Railway runs PostgreSQL, Redis, and Docker containers in a single dashboard with environment variable management. Auto-deploy from GitHub on merge to `dev` branch (staging) and manual trigger for production. Free tier is sufficient for SIH.
**Trade-off:** Railway free tier has sleep-on-idle behavior. Acceptable for demo — wake-up latency is under 5 seconds.

---

## System Architecture

```
┌─────────────────────────────────────────┐
│              User Channels              │
│  Web Chat │ WhatsApp │ Voice │ Portal   │
└─────────────────┬───────────────────────┘
                  │ HTTPS / WebSocket
┌─────────────────▼───────────────────────┐
│         FastAPI Gateway Layer           │
│  Auth │ Rate limit │ Lang detect │ Route│
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│           Core AI Engine                │
│  Intent Router → RAG Engine             │
│  Cutoff Predictor → Session Manager     │
│  Escalation Handler                     │
└──────┬──────────┬──────────┬────────────┘
       │          │          │
  pgvector     Redis       Langfuse
  (vectors)   (cache)    (observability)
       │
  PostgreSQL
  (structured)
       │
    AWS S3
   (raw PDFs)
```

---

## Tech Stack

| Layer | Package / Service | Version | Reason |
|---|---|---|---|
| Runtime | Python | 3.12 | Latest stable, async support |
| Web framework | FastAPI | latest | Auto OpenAPI, async, Pydantic |
| Data validation | Pydantic | v2 | Fast, strict, native FastAPI |
| ORM | SQLAlchemy | 2.x async | Async Postgres support |
| Migrations | Alembic | latest | Schema versioning |
| Vector DB | pgvector | 0.7+ | Postgres extension, cosine search |
| Primary LLM | DeepSeek V4 Flash | — | Cheapest frontier model, OAI-compatible |
| Fallback LLM | Groq / Llama 3.1 70B | — | Free, fastest inference |
| Embeddings | Gemini text-embedding-004 | — | Unlimited free via AI Studio |
| Observability | Langfuse | cloud free | LLM call tracing |
| Cache | Redis | 7.x | LLM response cache, session store |
| File storage | AWS S3 | — | Raw PDF storage before ingestion |
| PDF parsing | pypdf2 + pdfplumber | latest | Text + table extraction from PDFs |
| Background jobs | Celery + Redis | latest | Async document ingestion |
| Messaging | WhatsApp Cloud API | — | Meta direct, no BSP |
| Voice STT | OpenAI Whisper | — | Hindi + English speech-to-text |
| Voice TTS | gTTS | latest | Hindi + English text-to-speech |
| Frontend | React + Vite | latest | Chat widget + Admin CMS |
| UI | Tailwind CSS + shadcn/ui | latest | Team's existing stack |
| State | Zustand + TanStack Query | latest | Team's existing stack |
| Containerization | Docker + Docker Compose | latest | Full stack local dev |
| CI/CD | GitHub Actions | — | Lint → test → build → deploy |
| Deployment | Railway | — | Single dashboard for all services |
| Linting | Ruff | latest | Fastest Python linter |
| Formatting | Black | latest | Zero-config formatter |
| Type checking | mypy | latest | Static type safety |
| Testing | Pytest + httpx | latest | Async test client for FastAPI |

---

## Folder Structure

```
dte-chatbot/
│
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point, middleware registration
│   │   ├── config.py               # Settings via pydantic-settings (reads .env)
│   │   ├── dependencies.py         # FastAPI dependency injection (db, llm client, etc.)
│   │   │
│   │   ├── api/                    # Route handlers only — no business logic here
│   │   │   ├── __init__.py
│   │   │   ├── chat.py             # POST /chat — main query endpoint
│   │   │   ├── webhook.py          # POST /webhook — WhatsApp incoming messages
│   │   │   ├── ingest.py           # POST /ingest — document ingestion trigger
│   │   │   ├── admin.py            # GET/POST /admin/* — CMS endpoints
│   │   │   └── health.py           # GET /health — liveness probe
│   │   │
│   │   ├── services/               # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── rag.py              # RAG retrieval: embed → search → pack context
│   │   │   ├── llm.py              # LLM client: DeepSeek primary, Groq fallback
│   │   │   ├── embedder.py         # Gemini embedding calls
│   │   │   ├── ingestion.py        # PDF parse → chunk → embed → upsert
│   │   │   ├── escalation.py       # Confidence scoring + escalation logic
│   │   │   ├── cutoff.py           # REAP data query → rank-to-college mapping
│   │   │   ├── whatsapp.py         # WhatsApp Cloud API send/receive helpers
│   │   │   ├── session.py          # Conversation history via Redis
│   │   │   └── analytics.py        # Query logging, heatmap aggregation
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── college.py          # College, branch, seat matrix
│   │   │   ├── allotment.py        # REAP historical allotment (3 years)
│   │   │   ├── document.py         # Ingested document metadata
│   │   │   ├── ticket.py           # Escalation tickets
│   │   │   └── query_log.py        # Analytics: every query logged
│   │   │
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── chat.py             # ChatRequest, ChatResponse, StreamChunk
│   │   │   ├── ingest.py           # IngestRequest, IngestResponse
│   │   │   ├── webhook.py          # WhatsApp webhook payload schemas
│   │   │   ├── admin.py            # CollegeUpdate, FeeUpdate, etc.
│   │   │   └── analytics.py        # QueryStats, HeatmapResponse
│   │   │
│   │   ├── core/                   # Cross-cutting concerns
│   │   │   ├── __init__.py
│   │   │   ├── database.py         # Async SQLAlchemy engine + session factory
│   │   │   ├── redis.py            # Redis client singleton
│   │   │   ├── s3.py               # AWS S3 client + presigned URL helpers
│   │   │   ├── langfuse.py         # Langfuse client + trace decorators
│   │   │   ├── exceptions.py       # Custom exception classes
│   │   │   ├── middleware.py       # Request ID, CORS, rate limiting
│   │   │   └── logging.py          # Structured logging setup (structlog)
│   │   │
│   │   └── workers/                # Celery background task definitions
│   │       ├── __init__.py
│   │       ├── celery_app.py       # Celery app init
│   │       └── ingest_task.py      # Async document ingestion worker
│   │
│   ├── alembic/                    # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/               # Migration files go here
│   │
│   ├── tests/
│   │   ├── conftest.py             # Pytest fixtures (test DB, mock LLM client)
│   │   ├── test_chat.py
│   │   ├── test_rag.py
│   │   ├── test_ingest.py
│   │   ├── test_webhook.py
│   │   └── test_escalation.py
│   │
│   ├── prompts/                    # Prompt templates (versioned)
│   │   ├── system_prompt_en.txt
│   │   ├── system_prompt_hi.txt
│   │   └── cutoff_prompt.txt
│   │
│   ├── Dockerfile
│   ├── pyproject.toml              # Dependencies + tool config (ruff, black, mypy)
│   ├── .env.example
│   └── requirements.txt            # Pinned deps (generated from pyproject.toml)
│
├── frontend/                       # React + Vite
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatWidget.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   └── LanguageToggle.tsx
│   │   │   └── admin/
│   │   │       ├── CollegeEditor.tsx
│   │   │       ├── DocumentUploader.tsx
│   │   │       └── AnalyticsDashboard.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts          # TanStack Query + SSE streaming hook
│   │   │   └── useAnalytics.ts
│   │   ├── store/
│   │   │   └── chatStore.ts        # Zustand — local UI state
│   │   └── lib/
│   │       └── api.ts              # Axios instance + base URL config
│   ├── Dockerfile
│   └── package.json
│
├── data/                           # Data ingestion scripts (teammate 3 owns this)
│   ├── scrapers/
│   │   └── dte_scraper.py          # Scrape DTE website college data
│   ├── parsers/
│   │   └── reap_csv_parser.py      # Parse REAP allotment CSV (3 years)
│   ├── seeds/
│   │   └── seed_colleges.sql       # Initial college data seed
│   └── README.md                   # How to run ingestion scripts
│
├── infra/                          # DevOps config
│   ├── docker-compose.yml          # Full local stack
│   ├── docker-compose.test.yml     # Test environment (no volumes)
│   ├── nginx/
│   │   └── nginx.conf              # Reverse proxy config for production
│   └── railway/
│       └── railway.json            # Railway deployment config
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # PR CI: lint → test → docker build
│       └── deploy.yml              # Merge to dev → staging deploy
│
├── docs/
│   ├── architecture/
│   │   ├── system-diagram.md       # Mermaid diagrams (all 8)
│   │   └── adr/                    # Individual ADR files
│   ├── api/
│   │   └── openapi.json            # Auto-exported from FastAPI at /openapi.json
│   └── demo-script.md              # Updated every Friday before demo
│
├── .env.example                    # Root-level example (points to backend/.env.example)
├── .gitignore
├── Makefile                        # Dev shortcuts (make dev, make test, make lint)
└── README.md                       # This file
```

---

## Core Flows

### 1. Student query flow (happy path)

```
Student sends WhatsApp message
→ Meta webhook fires POST /webhook
→ Language detected (EN / HI / Hinglish)
→ Intent classified (admission / fee / cutoff / scholarship / other)
→ Query embedded via Gemini text-embedding-004
→ pgvector cosine search → top-5 chunks retrieved
→ Chunks + query sent to DeepSeek V4 Flash
→ Structured JSON response generated
→ Response sent back via WhatsApp Cloud API
→ Full trace logged to Langfuse
→ Query logged to analytics table
```

### 2. Admin document ingestion flow

```
Admin sends PDF to WhatsApp from whitelisted number
→ /webhook detects sender in ADMIN_NUMBERS + message type = document
→ Admin must also send /ingest command (not auto-triggered on raw PDF)
→ PDF downloaded from WhatsApp media URL
→ Uploaded to AWS S3 (raw PDF store)
→ Celery task queued: parse → chunk → embed → upsert to pgvector
→ Admin receives confirmation with chunk count
```

### 3. Cutoff prediction flow

```
Student: "meri rank 45000 hai OBC category, CS milega?"
→ Intent router classifies: CUTOFF_QUERY
→ Cutoff predictor service called (not RAG)
→ Query: SELECT colleges WHERE branch='CS' AND obc_cutoff_2024 >= 45000
→ Results ranked by historical allotment probability
→ Top 3 colleges returned with confidence range
→ Response formatted in Hindi (matching input language)
```

---

## WhatsApp Integration

### Setup

1. Create a Meta Developer account at `developers.facebook.com`
2. Create a new Business app → add WhatsApp product
3. Meta provides a **test sandbox phone number** at no cost for development
4. Set webhook URL to `https://your-domain/webhook`
5. Set webhook verify token (any string) — matches `WHATSAPP_VERIFY_TOKEN` in env
6. Business verification required to exceed 250 conversations/24h

### Free tier limits (as of 2026)

- **1,000 service conversations/month free** — service = user-initiated, you reply
- Without business verification: 250 conversations per 24 hours
- Since October 2025, limits are per Business Portfolio, not per number
- Document size limit: 100MB per file

### Webhook handler routing logic

```python
@router.post("/webhook")
async def whatsapp_webhook(payload: WhatsAppPayload):
    message = extract_message(payload)
    sender = message.sender_number

    # Admin routing
    if sender in settings.ADMIN_NUMBERS:
        if message.type == "document" and message.text == "/ingest":
            return await ingest_service.queue_document(message)
        if message.text.startswith("/stats"):
            return await analytics_service.send_summary(sender)

    # Student routing (all other senders)
    if message.type == "text":
        return await chat_service.handle_query(message)

    # Unsupported message type
    await whatsapp_service.send_text(sender,
        "I can only answer text questions. Please type your query.")
```

### Admin commands (from whitelisted numbers only)

| Command | Action |
|---|---|
| Send PDF + `/ingest` | Ingests document into RAG pipeline |
| `/stats` | Returns query count, top 5 intents, escalation rate |
| `/refresh` | Re-embeds all documents (full re-index) |
| `/health` | Returns system status |

---

## RAG Pipeline

### Ingestion path (runs on data update)

```
Source data (PDF / CSV / scraped HTML)
→ Validator: schema check, file type, size limit
→ PDF parser: pypdf2 for text, pdfplumber for tables
→ Chunker: 512-token fixed chunks, 50-token overlap
→ Embedder: Gemini text-embedding-004 → 768-dim vectors
→ Deduplicator: SHA-256 hash of chunk content → skip if exists
→ pgvector upsert: vector + metadata (source, page, college_id, date)
```

### Query path (every student message)

```
User query (text)
→ Embed query: Gemini text-embedding-004
→ pgvector cosine similarity search, top_k=5
→ Context packer: fit chunks into prompt window (max 4096 tokens)
→ LLM call: DeepSeek V4 Flash
→ Confidence scoring: check if answer is grounded in chunks
→ If confidence < 0.75: retry with top_k=8 (broader search)
→ If still < 0.75: escalate to human
→ Stream response tokens to user
```

### Chunking strategy

```python
CHUNK_SIZE = 512        # tokens
CHUNK_OVERLAP = 50      # tokens — prevents context loss at boundaries
EMBEDDING_DIM = 768     # Gemini text-embedding-004
TOP_K_DEFAULT = 5
TOP_K_BROAD = 8         # used on second attempt
CONFIDENCE_THRESHOLD = 0.75
```

### Redis caching

Identical queries (same embedding hash) skip the LLM call entirely and return cached response. TTL: 24 hours. Cache key: `SHA256(query_text + language)`.

---

## Escalation Logic

```
Query arrives
  ↓
RAG retrieval + confidence score
  ↓
confidence ≥ 0.75?
  ├─ YES → return grounded answer
  └─ NO  → broaden search (top_k=8, lower threshold)
              ↓
           still confident?
              ├─ YES → return answer + "(low confidence)" flag
              └─ NO  → escalate
                          ↓
                       generate ticket ID (UUID)
                       notify admin via WhatsApp (ADMIN_NUMBERS[0])
                       reply to student: ticket ID + "team will respond in 24h"
                       log full context to Langfuse + query_log table
```

**Escalation ticket contains:**
- Ticket ID
- Original query (text)
- Language detected
- Retrieved chunks (what the bot found)
- Confidence score
- Student phone number (for staff follow-up)
- Timestamp

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Never commit `.env`.

```bash
# App
APP_ENV=development                         # development | staging | production
APP_PORT=8000
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dte_chatbot
REDIS_URL=redis://localhost:6379/0

# LLM — Primary
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# LLM — Fallback
GROQ_API_KEY=your-groq-key
GROQ_MODEL=llama-3.1-70b-versatile

# Embeddings
GEMINI_API_KEY=your-gemini-key
GEMINI_EMBEDDING_MODEL=text-embedding-004

# WhatsApp
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_ACCESS_TOKEN=your-meta-access-token
WHATSAPP_VERIFY_TOKEN=your-webhook-verify-token
ADMIN_NUMBERS=+919876543210,+91XXXXXXXXXX    # comma-separated

# AWS S3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=ap-south-1
S3_BUCKET_NAME=dte-chatbot-docs

# Langfuse
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# RAG config
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K_DEFAULT=5
TOP_K_BROAD=8
CONFIDENCE_THRESHOLD=0.75
LLM_CACHE_TTL=86400                         # seconds (24h)
```

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Docker + Docker Compose
- Node.js 20+ (for frontend)
- `make` (optional but recommended)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/your-org/dte-chatbot.git
cd dte-chatbot

# 2. Start infrastructure (Postgres + pgvector + Redis)
docker compose up postgres redis -d

# 3. Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 4. Copy and fill environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Run migrations
alembic upgrade head

# 6. Install pgvector extension (one-time)
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 7. Start FastAPI dev server
uvicorn app.main:app --reload --port 8000

# 8. Frontend setup (separate terminal)
cd ../frontend
npm install
npm run dev

# 9. Start Celery worker (separate terminal)
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

### Makefile shortcuts

```bash
make dev        # Start backend + frontend + workers
make test       # Run pytest
make lint       # Run ruff + black check + mypy
make migrate    # Run alembic upgrade head
make seed       # Seed initial college data
```

### API docs

FastAPI auto-generates interactive docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

No manual spec file needed. Docs are always in sync with implementation.

---

## Docker Setup

### docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: dte
      POSTGRES_PASSWORD: dte_secret
      POSTGRES_DB: dte_chatbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dte"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: ./backend/.env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app         # hot reload in dev
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: ./backend
    env_file: ./backend/.env
    depends_on:
      - redis
      - postgres
    command: celery -A app.workers.celery_app worker --loglevel=info

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
```

### Backend Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[prod]"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## CI/CD Pipeline

### Branch strategy

| Branch | Purpose | Who merges |
|---|---|---|
| `main` | Production-ready only | Team lead (manual) |
| `dev` | Integration + staging deploy | Team lead after PR review |
| `feat/*` | One per feature, one per person | Self → PR to dev |
| `fix/<issue-number>` | Bug fixes | Self → PR to dev |

**Rules:**
- No direct pushes to `main` or `dev` — branch protection enforced
- Every change = PR
- PR must pass CI before merge
- Team lead reviews all PRs, merges within 4 hours of raise

### GitHub Actions CI (`.github/workflows/ci.yml`)

Runs on every PR targeting `dev`:

```yaml
name: CI

on:
  pull_request:
    branches: [dev]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: dte_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install deps
        run: pip install -e ".[dev]"
        working-directory: backend

      - name: Lint (ruff)
        run: ruff check .
        working-directory: backend

      - name: Format check (black)
        run: black --check .
        working-directory: backend

      - name: Type check (mypy)
        run: mypy app/
        working-directory: backend

      - name: Run tests
        run: pytest tests/ -v --tb=short
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost:5432/dte_test
          REDIS_URL: redis://localhost:6379/0

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build backend image
        run: docker build -t dte-backend ./backend
      - name: Build frontend image
        run: docker build -t dte-frontend ./frontend
```

---

## API Reference

All routes auto-documented at `/docs`. Key endpoints:

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/chat` | Main query endpoint (non-WhatsApp clients) | None |
| `POST` | `/webhook` | WhatsApp incoming message handler | Meta signature |
| `GET` | `/webhook` | WhatsApp webhook verification | Meta token |
| `POST` | `/ingest` | Trigger document ingestion (admin only) | Admin key header |
| `GET` | `/admin/colleges` | List all colleges | Admin key header |
| `PUT` | `/admin/colleges/{id}` | Update college data | Admin key header |
| `GET` | `/admin/analytics` | Query stats, heatmap data | Admin key header |
| `GET` | `/admin/tickets` | Escalation tickets list | Admin key header |
| `GET` | `/health` | Liveness probe | None |

### Chat request/response schema

```python
# Request
class ChatRequest(BaseModel):
    message: str
    language: Literal["en", "hi", "auto"] = "auto"
    session_id: str | None = None     # for conversation history

# Response (streaming SSE)
class StreamChunk(BaseModel):
    type: Literal["token", "done", "error"]
    content: str
    metadata: dict | None = None      # on "done": sources, confidence, ticket_id
```

---

## Team & Task Management

### Tool stack

| Tool | Purpose |
|---|---|
| GitHub Projects | Kanban: Backlog → In Progress → Review → Done |
| Notion (one page) | ADR log, env var names, demo script |
| WhatsApp group | Daily async standup |

### Daily standup (9 AM, WhatsApp, async)

```
1. Done yesterday:
2. Doing today:
3. Blocked? (yes/no — if yes, what)
4. PR ready for review? (link)
```

### Weekly rhythm

- **Monday** — 15 min call: assign week's GitHub issues, call out dependencies early
- **Friday** — 30 min call: demo dry-run, update demo script, merge stable branches to dev

### Team split

| Person | Owns |
|---|---|
| Nithishkumar | FastAPI backend, RAG pipeline, pgvector, Docker, CI/CD, OpenAPI, Langfuse, cutoff predictor |
| Teammate 2 | React chat UI, Admin CMS, SSE streaming integration, language toggle |
| Teammate 3 | Data collection, PDF parsing, CSV ingestion scripts, WhatsApp/Telegram connector |

### GitHub issue rules

- One issue = max one day of work. If bigger, split it.
- Every issue assigned to exactly one person.
- Labels: `feature` `bug` `devops` `data` `blocked`
- Milestones: Week 1 (RAG working end-to-end), Week 2 (all demo features), Week 3 (polish + deploy)

---

## Production Checklist

Before demo day, verify every item.

### Security
- [ ] `SECRET_KEY` is a random 64-char string, not a placeholder
- [ ] `ADMIN_NUMBERS` contains only real team numbers
- [ ] `.env` is in `.gitignore` and never committed
- [ ] WhatsApp webhook validates Meta signature on every request
- [ ] Rate limiting enabled on all public endpoints (FastAPI `slowapi`)
- [ ] CORS configured to allow only your frontend domain
- [ ] No API keys hardcoded anywhere in source code

### Reliability
- [ ] DeepSeek fallback to Groq is tested and working
- [ ] Redis cache TTL set correctly (24h)
- [ ] Celery worker has retry logic on ingestion failure (max 3 retries)
- [ ] Database connection pool configured (`pool_size=10, max_overflow=20`)
- [ ] `/health` endpoint returns 200 and checked by Railway health probe
- [ ] Alembic migrations run on deploy (not manually)
- [ ] pgvector index created: `CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)`

### Observability
- [ ] Langfuse traces appearing for every LLM call
- [ ] Structured logging enabled (structlog, JSON output in production)
- [ ] Every escalation generates a Langfuse trace with full context
- [ ] Analytics table receiving query log entries

### Data
- [ ] At minimum: 50 college records seeded
- [ ] At minimum: 2 years of REAP allotment data loaded
- [ ] At minimum: 10 DTE PDFs ingested (fee structure, scholarship schemes)
- [ ] Redis reachable from backend container
- [ ] pgvector extension installed and verified: `SELECT * FROM pg_extension WHERE extname='vector'`

### Demo
- [ ] Demo script updated and rehearsed
- [ ] Fallback screenshots ready if WhatsApp API is slow
- [ ] Hindi query demo working: "Rajasthan mein BE CS ke liye kitni rank chahiye"
- [ ] Cutoff predictor demo working with real 2024 REAP data
- [ ] Escalation flow demo working (trigger with unknown college name)
- [ ] Admin CMS demo: update a fee, show it reflected in bot response
- [ ] Analytics dashboard showing at least 7 days of synthetic query data

---

## Notes on extending post-SIH

The backend is structured to extend without rewriting:

- **More channels:** Add a new route file under `api/` and wire to the same `chat_service.handle_query()`. Telegram bot = 1 new file.
- **More intents:** Add a new entry in the intent classifier prompt + a new service method. No architecture change.
- **Better LLM:** Change `DEEPSEEK_MODEL` env var. Zero code change — the LLM client is abstracted.
- **Production embeddings:** Swap `GEMINI_EMBEDDING_MODEL` for any OpenAI-compatible embedding endpoint. One line change in `embedder.py`.
- **Multi-tenant (multiple states):** Add a `tenant_id` column to `documents` and `query_log`, filter by it in all queries. pgvector supports filtered search natively.

---

*Last updated: July 2026 | SIH 2025 — Problem Statement 1631 | Team: Nithishkumar Anandharaj + 2*
