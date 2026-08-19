# Coligo Administration Portal

Streamlit front end for the Coligo college admission backend. Two roles:

- **College** — sign up, then manage your profile, courses, infrastructure/facilities,
  and PDF brochures. All data is stored in the backend (Postgres) via the FastAPI API.
- **Admin** — fixed login (`admin@coligo.com` / `coligo@123`, configurable via the
  `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars on the backend). Read-only view of every
  registered college and its courses/brochures/facilities.

## Prerequisites

1. The FastAPI backend must be running (from the repo root):

   ```bash
   pip install -e .
   cp .env.example .env   # adjust DATABASE_URL etc.
   uvicorn api.main:app --reload
   ```

   The backend needs a Postgres database with the `vector` extension available
   (see the repo root `README.md` / `docker-compose.yml`). On startup (in
   `ENVIRONMENT=development`) it auto-creates all tables, including the new
   `colleges`, `courses`, `facilities`, and `brochures` tables.

2. Install the portal's own dependencies:

   ```bash
   cd "administration portal"
   pip install -r requirements.txt
   ```

## Running

```bash
cd "administration portal"
streamlit run app.py
```

By default the portal talks to `http://localhost:8000`. Point it elsewhere with:

```bash
# Windows PowerShell
$env:COLIGO_API_BASE_URL = "http://localhost:8000"
# bash
export COLIGO_API_BASE_URL=http://localhost:8000
```

## Notes

- Uploaded logos and brochures are stored on disk under `uploads/` at the backend
  repo root (configurable via `UPLOAD_DIR`), and referenced from Postgres.
- Brochures must be PDF files; logos must be PNG/JPG.
- Admin credentials are fixed/seeded via backend settings, not stored in the
  `colleges` table — there's no admin signup flow.
